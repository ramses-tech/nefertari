import json
import logging
import simplejson
from collections import defaultdict

import six
from six.moves import urllib
from pyramid.request import Request

from nefertari.json_httpexceptions import (
    JHTTPBadRequest, JHTTPNotFound, JHTTPMethodNotAllowed)
from nefertari.utils import dictset, merge_dicts, str2dict
from nefertari import wrappers, engine
from nefertari.resource import ACTIONS
from nefertari.view_helpers import OptionsViewMixin, ESAggregator
from nefertari.events import trigger_before_events


log = logging.getLogger(__name__)


class ViewMapper(object):
    "Custom mapper class for BaseView"

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __call__(self, view):
        # i.e index, create etc.
        action_name = self.kwargs['attr']

        def view_mapper_wrapper(context, request):
            matchdict = request.matchdict.copy()
            matchdict.pop('action', None)
            matchdict.pop('traverse', None)

            # instance of BaseView (or child of)
            view_obj = view(context, request)
            action = getattr(view_obj, action_name)
            request.action = action_name

            # Tunneled collection PATCH/PUT doesn't support query params
            tunneled = getattr(request, '_tunneled_get', False)
            if tunneled and action_name in ('update_many',):
                view_obj._query_params = dictset()

            # we should not run "after_calls" here, so lets save them in
            # request as filters they will be ran in the renderer factory
            request.filters = view_obj._after_calls

            try:
                # run before_calls (validators) before running the action
                for call in view_obj._before_calls.get(action_name, []):
                    call(request=request)

            except wrappers.ValidationError as e:
                log.error('validation error: %s', e)
                raise JHTTPBadRequest(e.args)

            except wrappers.ResourceNotFound as e:
                log.error('resource not found: %s', e)
                raise JHTTPNotFound()

            trigger_before_events(view_obj)
            return action(**matchdict)

        return view_mapper_wrapper


class BaseView(OptionsViewMixin):
    """Base class for nefertari views.
    """
    __view_mapper__ = ViewMapper
    _default_renderer = 'nefertari_json'
    _json_encoder = None
    Model = None

    @staticmethod
    def convert_dotted(params):
        """ Convert dotted keys in :params: dictset to a nested dictset.

        E.g. {'settings.foo': 'bar'} -> {'settings': {'foo': 'bar'}}
        """
        if not isinstance(params, dictset):
            params = dictset(params)

        dotted_items = {k: v for k, v in params.items() if '.' in k}

        if dotted_items:
            dicts = [str2dict(key, val) for key, val in dotted_items.items()]
            dotted = six.functools.reduce(merge_dicts, dicts)
            params = params.subset(['-' + k for k in dotted_items.keys()])
            params.update(dict(dotted))

        return params

    def __init__(self, context, request, _query_params={}, _json_params={}):
        """ Prepare data to be used across the view and run init methods.

        Each view has these dicts on data:
          :_query_params: Params from a query string
          :_json_params: Request JSON data. Populated only for
              PUT, PATCH, POST methods
          :_params: Join of _query_params and _json_params

        For method tunneling, _json_params contains the same data as
        _query_params.
        """
        self.context = context
        self.request = request

        self.prepare_request_params(_query_params, _json_params)

        # dict of the callables {'action':[callable1, callable2..]}
        # as name implies, before calls are executed before the action is
        # called after_calls are called after the action returns.
        self._before_calls = defaultdict(list)
        self._after_calls = defaultdict(list)

        self.set_override_rendered()

        root_resource = getattr(self, 'root_resource', None)
        self._auth_enabled = root_resource is not None and root_resource.auth

        self._run_init_actions()
        if self.request.method == 'GET':
            self._setup_aggregation()

    def _run_init_actions(self):
        self.setup_default_wrappers()
        self.convert_ids2objects()
        self.set_public_limits()
        if self.request.method == 'PUT':
            self.fill_null_values()

    def prepare_request_params(self, _query_params, _json_params):
        """ Prepare query and update params. """
        self._query_params = dictset(
            _query_params or self.request.params.mixed())
        self._json_params = dictset(_json_params)

        ctype = self.request.content_type
        if self.request.method in ['POST', 'PUT', 'PATCH']:
            if ctype == 'application/json':
                try:
                    self._json_params.update(self.request.json)
                except simplejson.JSONDecodeError:
                    log.error(
                        "Expecting JSON. Received: '{}'. "
                        "Request: {} {}".format(
                            self.request.body, self.request.method,
                            self.request.url))

            self._json_params = BaseView.convert_dotted(self._json_params)
            self._query_params = BaseView.convert_dotted(self._query_params)

        self._params = self._query_params.copy()
        self._params.update(self._json_params)

    def set_override_rendered(self):
        """ Set self.request.override_renderer if needed. """
        if '' in self.request.accept:
            self.request.override_renderer = self._default_renderer
        elif 'application/json' in self.request.accept:
            self.request.override_renderer = 'nefertari_json'
        elif 'text/plain' in self.request.accept:
            self.request.override_renderer = 'string'

    def _setup_aggregation(self, aggregator=None):
        """ Wrap `self.index` method with ESAggregator.

        This makes `self.index` to first try to run aggregation and only
        on fail original method is run. Method is wrapped only if it is
        defined and `elasticsearch.enable_aggregations` setting is true.
        """
        from nefertari.elasticsearch import ES
        if aggregator is None:
            aggregator = ESAggregator
        aggregations_enabled = (
            ES.settings and ES.settings.asbool('enable_aggregations'))
        if not aggregations_enabled:
            log.debug('Elasticsearch aggregations are not enabled')
            return

        index = getattr(self, 'index', None)
        index_defined = index and index != self.not_allowed_action
        if index_defined:
            self.index = aggregator(self).wrap(self.index)

    def get_collection_es(self):
        """ Query ES collection and return results.

        This is default implementation of querying ES collection with
        `self._query_params`. It must return found ES collection
        results for default response renderers to work properly.
        """
        from nefertari.elasticsearch import ES
        return ES(self.Model.__name__).get_collection(**self._query_params)

    def fill_null_values(self):
        """ Fill missing model fields in JSON with {key: null value}.

        Only run for PUT requests.
        """
        if not self.Model:
            log.info("%s has no model defined" % self.__class__.__name__)
            return

        empty_values = self.Model.get_null_values()
        for field, value in empty_values.items():
            if field not in self._json_params:
                self._json_params[field] = value

    def set_public_limits(self):
        """ Set public limits if auth is enabled and user is not
        authenticated.

        Also sets default limit for GET, HEAD requests.
        """
        if self.request.method.upper() in ['GET', 'HEAD']:
            self._query_params.process_int_param('_limit', 20)
        if self._auth_enabled and not getattr(self.request, 'user', None):
            wrappers.set_public_limits(self)

    def convert_ids2objects(self):
        """ Convert object IDs from `self._json_params` to objects if needed.

        Only IDs that belong to relationship field of `self.Model`
        are converted.
        """
        if not self.Model:
            log.info("%s has no model defined" % self.__class__.__name__)
            return

        for field in self._json_params.keys():
            if not engine.is_relationship_field(field, self.Model):
                continue
            rel_model_cls = engine.get_relationship_cls(field, self.Model)
            self.id2obj(field, rel_model_cls)

    def setup_default_wrappers(self):
        """ Setup defaulf wrappers.

        Wrappers are applied when view method does not return instance
        of Response. In this case nefertari renderers call wrappers and
        handle response generation.
        """
        # Index
        self._after_calls['index'] = [
            wrappers.wrap_in_dict(self.request),
            wrappers.add_meta(self.request),
            wrappers.add_object_url(self.request),
        ]

        # Show
        self._after_calls['show'] = [
            wrappers.wrap_in_dict(self.request),
            wrappers.add_meta(self.request),
            wrappers.add_object_url(self.request),
        ]

        # Create
        self._after_calls['create'] = [
            wrappers.wrap_in_dict(self.request),
            wrappers.add_meta(self.request),
            wrappers.add_object_url(self.request),
        ]

        # Update
        self._after_calls['update'] = [
            wrappers.wrap_in_dict(self.request),
            wrappers.add_meta(self.request),
            wrappers.add_object_url(self.request),
        ]

        # Replace
        self._after_calls['replace'] = [
            wrappers.wrap_in_dict(self.request),
            wrappers.add_meta(self.request),
            wrappers.add_object_url(self.request),
        ]

        # Privacy wrappers
        if self._auth_enabled:
            for meth in ('index', 'show', 'create', 'update', 'replace'):
                self._after_calls[meth] += [
                    wrappers.apply_privacy(self.request),
                ]
            for meth in ('update', 'replace', 'update_many'):
                self._before_calls[meth] += [
                    wrappers.apply_request_privacy(
                        self.Model, self._json_params),
                ]

    def __getattr__(self, attr):
        if attr in ACTIONS:
            return self.not_allowed_action

        raise AttributeError(attr)

    def not_allowed_action(self, *a, **k):
        raise JHTTPMethodNotAllowed()

    def add_before_or_after_call(self, action, _callable, pos=None,
                                 before=True):
        if not six.callable(_callable):
            raise ValueError('%s is not a callable' % _callable)

        if before:
            callkind = self._before_calls
        else:
            callkind = self._after_calls

        if pos is None:
            callkind[action].append(_callable)
        else:
            callkind[action].insert(pos, _callable)

    add_before_call = lambda self, *a, **k: self.add_before_or_after_call(
        *a, before=True, **k)
    add_after_call = lambda self, *a, **k: self.add_before_or_after_call(
        *a, before=False, **k)

    def subrequest(self, url, params={}, method='GET'):
        req = Request.blank(url, cookies=self.request.cookies,
                            content_type='application/json',
                            method=method)

        if method == 'GET' and params:
            req.body = urllib.parse.urlencode(params)

        if method == 'POST':
            req.body = json.dumps(params)

        return self.request.invoke_subrequest(req)

    def id2obj(self, name, model, pk_field=None, setdefault=None):
        if name not in self._json_params:
            return

        if pk_field is None:
            pk_field = model.pk_field()

        def _get_object(id_):
            if hasattr(id_, 'pk_field'):
                return id_

            obj = model.get_item(
                **{pk_field: id_, '_raise_on_empty': False})
            if setdefault:
                return obj or setdefault
            else:
                if not obj:
                    raise JHTTPBadRequest('id2obj: Object %s not found' % id_)
                return obj

        ids = self._json_params[name]
        if not ids:
            return
        if isinstance(ids, list):
            self._json_params[name] = []
            for _id in ids:
                obj = _id if _id is None else _get_object(_id)
                self._json_params[name].append(obj)
        else:
            self._json_params[name] = ids if ids is None else _get_object(ids)


def key_error_view(context, request):
    return JHTTPBadRequest("Bad or missing param '%s'" % context.args[0])


def value_error_view(context, request):
    return JHTTPBadRequest("Bad or missing value '%s'" % context.args[0])


def error_view(context, request):
    return JHTTPBadRequest(context.args[0])


def includeme(config):
    config.add_view(key_error_view, context=KeyError)
    config.add_view(value_error_view, context=ValueError)
    config.add_view(error_view, context=Exception)
