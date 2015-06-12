import json
import logging
import simplejson
from collections import defaultdict

import six
from six.moves import urllib
from pyramid.settings import asbool
from pyramid.request import Request

from nefertari.json_httpexceptions import (
    JHTTPBadRequest, JHTTPNotFound, JHTTPMethodNotAllowed)
from nefertari.utils import dictset, merge_dicts, str2dict
from nefertari import wrappers, engine
from nefertari.resource import ACTIONS

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

            return action(**matchdict)

        return view_mapper_wrapper


class BaseView(object):
    """Base class for nefertari views.
    """

    __view_mapper__ = ViewMapper
    _default_renderer = 'nefertari_json'
    _json_encoder = None
    _model_class = None

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
        self._query_params = dictset(_query_params or request.params.mixed())
        self._json_params = dictset(_json_params)

        ctype = request.content_type
        if request.method in ['POST', 'PUT', 'PATCH']:
            if ctype == 'application/json':
                try:
                    self._json_params.update(request.json)
                except simplejson.JSONDecodeError:
                    log.error(
                        "Expecting JSON. Received: '{}'. "
                        "Request: {} {}".format(
                            request.body, request.method, request.url))

            self._json_params = BaseView.convert_dotted(self._json_params)
            self._query_params = BaseView.convert_dotted(self._query_params)

        self._params = self._query_params.copy()
        self._params.update(self._json_params)

        # dict of the callables {'action':[callable1, callable2..]}
        # as name implies, before calls are executed before the action is
        # called after_calls are called after the action returns.
        self._before_calls = defaultdict(list)
        self._after_calls = defaultdict(list)

        # no accept headers, use default
        if '' in request.accept:
            request.override_renderer = self._default_renderer
        elif 'application/json' in request.accept:
            request.override_renderer = 'nefertari_json'
        elif 'text/plain' in request.accept:
            request.override_renderer = 'string'

        if '_refresh_index' in self._query_params:
            self.refresh_index = self._query_params.asbool(
                '_refresh_index', pop=True)
        else:
            self.refresh_index = None

        root_resource = getattr(self, 'root_resource', None)
        self._auth_enabled = root_resource is not None and root_resource.auth

        self._run_init_actions()

    def _run_init_actions(self):
        self.setup_default_wrappers()
        self.convert_ids2objects()
        self.set_public_limits()
        if self.request.method == 'PUT':
            self.fill_null_values()

    def fill_null_values(self, model_cls=None):
        """ Fill missing model fields in JSON with {key: None}.

        Only run for PUT requests.
        """
        if model_cls is None:
            model_cls = self._model_class
        if not model_cls:
            log.info("%s has no model defined" % self.__class__.__name__)
            return

        empty_values = model_cls.get_null_values()
        for field, value in empty_values.items():
            if field not in self._json_params:
                self._json_params[field] = value

    def set_public_limits(self):
        """ Set public limits if auth is enabled and user is not
        authenticated.
        """
        if self._auth_enabled and not getattr(self.request, 'user', None):
            wrappers.set_public_limits(self)

    def convert_ids2objects(self, model_cls=None):
        """ Convert object IDs from `self._json_params` to objects if needed.

        Only IDs that belong to relationship field of `self._model_class`
        are converted.
        """
        if model_cls is None:
            model_cls = self._model_class
        if not model_cls:
            log.info("%s has no model defined" % self.__class__.__name__)
            return

        for field in self._json_params.keys():
            if not engine.is_relationship_field(field, model_cls):
                continue
            rel_model_cls = engine.get_relationship_cls(field, model_cls)
            self.id2obj(field, rel_model_cls)

    def get_debug(self, package=None):
        if not package:
            key = 'debug'
        else:
            key = '%s.debug' % package.split('.')[0]
        return asbool(self.request.registry.settings.get(key))

    def setup_default_wrappers(self):
        self._after_calls['index'] = [
            wrappers.wrap_in_dict(self.request),
            wrappers.add_meta(self.request),
        ]
        if self._auth_enabled:
            self._after_calls['index'] += [
                wrappers.apply_privacy(self.request),
            ]
        self._after_calls['index'] += [
            wrappers.add_etag(self.request),
        ]

        self._after_calls['show'] = [
            wrappers.wrap_in_dict(self.request),
            wrappers.add_meta(self.request),
        ]
        if self._auth_enabled:
            self._after_calls['show'] += [
                wrappers.apply_privacy(self.request),
            ]

        self._after_calls['delete'] = [
            wrappers.add_confirmation_url(self.request)
        ]

        self._after_calls['delete_many'] = [
            wrappers.add_confirmation_url(self.request)
        ]

        self._after_calls['update_many'] = [
            wrappers.add_confirmation_url(self.request)
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

    def needs_confirmation(self):
        return '__confirmation' not in self._query_params

    def id2obj(self, name, model, pk_field=None, setdefault=None):
        if name not in self._json_params:
            return

        if pk_field is None:
            pk_field = model.pk_field()

        def _get_object(id_):
            if hasattr(id_, 'pk_field'):
                return id_

            obj = model.get(**{pk_field: id_})
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


class ESAggregationMixin(object):
    """ Mixin that provides methods to perform Elasticsearch aggregations.

    Should be mixed with subclasses of `nefertari.view.BaseView`.

    To use aggregation at collection route requests, simply return
    `self.aggregate()`.

    Attributes:
        :_aggregations_keys: Sequence of strings representing name(s) of the
            root key under which aggregations names are defined. Order of keys
            matters - first key found in request is popped and returned.
        :_auth_enabled: Boolean indicating whether authentication is enabled.
            Is calculated in BaseView.

    Examples:
        If _aggregations_keys=('_aggregations',), then query string params
        should look like:
            _aggregations.min_price.min.field=price
    """
    _aggregations_keys = ('_aggregations', '_aggs')
    _auth_enabled = None

    def pop_aggregations_params(self):
        """ Pop and return aggregation params from query string params.

        Aggregation params are expected to be prefixed(nested under) by
        any of `self._aggregations_keys`.
        """
        self._query_params = BaseView.convert_dotted(self._query_params)

        for key in self._aggregations_keys:
            if key in self._query_params:
                return self._query_params.pop(key)
        else:
            raise KeyError('Missing aggregation params')

    def stub_wrappers(self):
        """ Remove default 'index' after call wrappers and add only
        those needed for aggregation results output.
        """
        self._after_calls['index'] = []

    @classmethod
    def get_aggregations_fields(cls, params):
        """ Recursively get values under the 'field' key.

        Is used to get names of fields on which aggregations should be
        performed.
        """
        fields = []
        for key, val in params.items():
            if isinstance(val, dict):
                fields += cls.get_aggregations_fields(val)
            if key == 'field':
                fields.append(val)
        return fields

    def check_aggregations_privacy(self, aggregations_params):
        """ Check per-field privacy rules in aggregations.

        Privacy is checked by making sure user has access to the fields
        used in aggregations.
        """
        fields = self.get_aggregations_fields(aggregations_params)
        fields_dict = dictset.fromkeys(fields)
        fields_dict['_type'] = self._model_class.__name__

        wrapper = wrappers.apply_privacy(self.request)
        allowed_fields = set(wrapper(result=fields_dict).keys())
        not_allowed_fields = set(fields) - set(allowed_fields)

        if not_allowed_fields:
            err = 'Not enough permissions to aggregate on fields: {}'.format(
                ','.join(not_allowed_fields))
            raise ValueError(err)

    def aggregate(self):
        """ Perform aggregation and return response. """
        from nefertari.elasticsearch import ES
        if not ES.settings.asbool('enable_aggregations'):
            log.warn('Elasticsearch aggregations are disabled')
            raise KeyError('Elasticsearch aggregations are disabled')

        aggregations_params = self.pop_aggregations_params()
        if self._auth_enabled:
            self.check_aggregations_privacy(aggregations_params)
        self.stub_wrappers()

        search_params = []
        if 'q' in self._query_params:
            search_params.append(self._query_params.pop('q'))
        _raw_terms = ' AND '.join(search_params)

        return ES(self._model_class.__name__).aggregate(
            _aggregations_params=aggregations_params,
            _raw_terms=_raw_terms,
            **self._query_params
        )


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
