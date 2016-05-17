import json
import logging
from datetime import date, datetime

from nefertari import wrappers
from nefertari.utils import get_json_encoder
from nefertari.json_httpexceptions import JHTTPOk, JHTTPCreated
from nefertari.events import trigger_after_events

log = logging.getLogger(__name__)


class _JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.strftime("%Y-%m-%dT%H:%M:%SZ")  # iso

        try:
            return super(_JSONEncoder, self).default(obj)
        except TypeError:
            return str(obj)  # fallback to str


class JsonRendererFactory(object):

    def __init__(self, info):
        """ Constructor: info will be an object having the
        following attributes: name (the renderer name), package
        (the package that was 'current' at the time the
        renderer was registered), type (the renderer type
        name), registry (the current application registry) and
        settings (the deployment settings dictionary). """
        pass

    def _set_content_type(self, system):
        """ Set response content type """
        request = system.get('request')
        if request:
            response = request.response
            ct = response.content_type
            if ct == response.default_content_type:
                response.content_type = 'application/json'

    def _render_response(self, value, system):
        """ Render a response """
        view = system['view']
        enc_class = getattr(view, '_json_encoder', None)
        if enc_class is None:
            enc_class = get_json_encoder()
        return json.dumps(value, cls=enc_class)

    def __call__(self, value, system):
        """ Call the renderer implementation with the value
        and the system value passed in as arguments and return
        the result (a string or unicode object). The value is
        the return value of a view.  The system value is a
        dictionary containing available system values
        (e.g. view, context, and request).
        """
        self._set_content_type(system)
        # run after_calls on the value before jsonifying
        value = self.run_after_calls(value, system)
        value = self._trigger_events(value, system)
        return self._render_response(value, system)

    def _trigger_events(self, value, system):
        view_obj = system['view'](system['context'], system['request'])
        view_obj._response = value
        evt = trigger_after_events(view_obj)
        return evt.response

    def run_after_calls(self, value, system):
        request = system.get('request')
        if request and hasattr(request, 'action'):

            if request.action in ['index', 'show']:
                value = wrappers.wrap_in_dict(request)(result=value)

        return value


class DefaultResponseRendererMixin(object):
    """ Renderer mixin that generates responses for all create/update/delete
    view methods.
    """
    def _get_common_kwargs(self, system):
        """ Get kwargs common for all methods. """
        enc_class = getattr(system['view'], '_json_encoder', None)
        if enc_class is None:
            enc_class = get_json_encoder()
        return {
            'request': system['request'],
            'encoder': enc_class,
        }

    def _get_create_update_kwargs(self, value, common_kw):
        """ Get kwargs common to create, update, replace. """
        kw = common_kw.copy()
        kw['body'] = value
        if '_self' in value:
            kw['headers'] = [('Location', value['_self'])]
        return kw

    def render_create(self, value, system, common_kw):
        """ Render response for view `create` method (collection POST) """
        kw = self._get_create_update_kwargs(value, common_kw)
        return JHTTPCreated(**kw)

    def render_update(self, value, system, common_kw):
        """ Render response for view `update` method (item PATCH) """
        kw = self._get_create_update_kwargs(value, common_kw)
        return JHTTPOk('Updated', **kw)

    def render_replace(self, *args, **kwargs):
        """ Render response for view `replace` method (item PUT) """
        return self.render_update(*args, **kwargs)

    def render_delete(self, value, system, common_kw):
        """ Render response for view `delete` method (item DELETE) """
        return JHTTPOk('Deleted', **common_kw.copy())

    def render_delete_many(self, value, system, common_kw):
        """ Render response for view `delete_many` method (collection DELETE)
        """
        if isinstance(value, dict):
            return JHTTPOk(extra=value)
        msg = 'Deleted {} {}(s) objects'.format(
            value, system['view'].Model.__name__)
        return JHTTPOk(msg, **common_kw.copy())

    def render_update_many(self, value, system, common_kw):
        """ Render response for view `update_many` method
        (collection PUT/PATCH)
        """
        msg = 'Updated {} {}(s) objects'.format(
            value, system['view'].Model.__name__)
        return JHTTPOk(msg, **common_kw.copy())

    def _render_response(self, value, system):
        """ Handle response rendering.

        Calls mixin methods according to request.action value.
        """
        super_call = super(DefaultResponseRendererMixin, self)._render_response
        try:
            method_name = 'render_{}'.format(system['request'].action)
        except (KeyError, AttributeError):
            return super_call(value, system)
        method = getattr(self, method_name, None)
        if method is not None:
            common_kw = self._get_common_kwargs(system)
            response = method(value, system, common_kw)
            system['request'].response = response
            return
        return super_call(value, system)


class NefertariJsonRendererFactory(DefaultResponseRendererMixin,
                                   JsonRendererFactory):
    """ Special json renderer which will apply all after_calls(filters)
    to the result.
    """
    def run_after_calls(self, value, system):
        request = system.get('request')
        if request and hasattr(request, 'action'):
            after_calls = getattr(request, 'filters', {})
            for call in after_calls.get(request.action, []):
                value = call(**dict(request=request, result=value))
        return value
