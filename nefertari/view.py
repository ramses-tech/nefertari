import json
import logging
import urllib
import simplejson
from collections import defaultdict
from pyramid.settings import asbool
from pyramid.request import Request

from nefertari.json_httpexceptions import *
from nefertari.utils import dictset
from nefertari import wrappers
from nefertari.resource import ACTIONS

log = logging.getLogger(__name__)


class ViewMapper(object):
    "Custom mapper class for BaseView"

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __call__(self, view):
        #i.e index, create etc.
        action_name = self.kwargs['attr']

        def view_mapper_wrapper(context, request):
            matchdict = request.matchdict.copy()
            matchdict.pop('action', None)
            matchdict.pop('traverse', None)

            #instance of BaseView (or child of)
            view_obj = view(context, request)
            action = getattr(view_obj, action_name)
            request.action = action_name

            # we should not run "after_calls" here, so lets save them in request
            # as filters they will be ran in the renderer factory
            request.filters = view_obj._after_calls

            try:
                # run before_calls (validators) before running the action
                for call in view_obj._before_calls.get(action_name, []):
                    call(request=request)

            except wrappers.ValidationError, e:
                log.error('validation error: %s', e)
                raise JHTTPBadRequest(e.args)

            except wrappers.ResourceNotFound, e:
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

    def __init__(self, context, request, _params={}):
        self.context = context
        self.request = request

        self._params = dictset(_params or request.params.mixed())

        ctype = request.content_type
        if request.method in ['POST', 'PUT', 'PATCH']:
            if ctype == 'application/json':
                try:
                    self._params.update(request.json)
                except simplejson.JSONDecodeError:
                    log.error(
                        "Expecting JSON. Received: '{}'. Request: {} {}".format(
                            request.body, request.method, request.url))

        # dict of the callables {'action':[callable1, callable2..]}
        # as name implies, before calls are executed before the action is called
        # after_calls are called after the action returns.
        self._before_calls = defaultdict(list)
        self._after_calls = defaultdict(list)

        # no accept headers, use default
        if '' in request.accept:
            request.override_renderer = self._default_renderer

        elif 'application/json' in request.accept:
            request.override_renderer = 'nefertari_json'

        elif 'text/plain' in request.accept:
            request.override_renderer = 'string'

        self.setup_default_wrappers()
        self.convert_ids2objects()

        if not getattr(self.request, 'user', None):
            wrappers.set_public_limits(self)

    def convert_ids2objects(self):
        """ Convert object IDs from `self._params` to objects if needed.

        Only IDs tbat belong to relationship field of `self._model_class`
        are converted.
        """
        from nefertari.engine import is_relationship_field, relationship_cls
        for field in self._params.keys():
            if not is_relationship_field(field, self._model_class):
                continue
            model_cls = relationship_cls(field, self._model_class)
            self.id2obj(field, model_cls)

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
            wrappers.add_etag(self.request),
        ]

        self._after_calls['show'] = [
            wrappers.wrap_in_dict(self.request),
            wrappers.add_meta(self.request),
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
        if not callable(_callable):
            raise ValueError('%s is not a callable' % _callable)

        if before:
            callkind = self._before_calls
        else:
            callkind = self._after_calls

        if pos is None:
            callkind[action].append(_callable)
        else:
            callkind[action].insert(pos, _callable)

    add_before_call = lambda self, *a, **k: self.add_before_or_after_call(*a, before=True, **k)
    add_after_call = lambda self, *a, **k: self.add_before_or_after_call(*a, before=False, **k)

    def subrequest(self, url, params={}, method='GET'):
        req = Request.blank(url, cookies=self.request.cookies,
                            content_type='application/json',
                            method=method)

        if req.method == 'GET' and params:
            req.body = urllib.urlencode(params)

        if req.method == 'POST':
            req.body = json.dumps(params)

        return self.request.invoke_subrequest(req)

    def needs_confirmation(self):
        return '__confirmation' not in self._params

    def delete_many(self, **kw):
        if not self._model_class:
            log.error("%s _model_class in invalid: %s" % (
                self.__class__.__name__, self._model_class))
            raise JHTTPBadRequest

        objs = self._model_class.get_collection(**self._params)

        if self.needs_confirmation():
            return objs

        count = self._model_class.count(objs)
        self._model_class._delete_many(objs)
        return JHTTPOk("Deleted %s %s objects" % (
            count, self._model_class.__name__))

    def id2obj(self, name, model, id_field=None, setdefault=None):
        if name not in self._params:
            return

        if id_field is None:
            id_field = model.id_field()

        def _get_object(id_):
            if isinstance(id_, model):
                return id_

            obj = model.get(**{id_field: id_})
            if setdefault:
                return obj or setdefault
            else:
                if not obj:
                    raise JHTTPBadRequest('id2obj: Object %s not found' % id_)
                return obj

        ids = self._params[name]
        if isinstance(ids, list):
            self._params[name] = [_get_object(_id) for _id in ids]
        else:
            self._params[name] = _get_object(ids)


def key_error_view(context, request):
    return JHTTPBadRequest("Bad or missing param '%s'" % context.message)


def value_error_view(context, request):
    return JHTTPBadRequest("Bad or missing value '%s'" % context.message)


def error_view(context, request):
    return JHTTPBadRequest(context.message)


def includeme(config):
    config.add_view(key_error_view, context=KeyError)
    config.add_view(value_error_view, context=ValueError)
    config.add_view(error_view, context=Exception)
