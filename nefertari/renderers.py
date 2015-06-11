import json
import logging
from datetime import date, datetime

from nefertari import wrappers
from pyramid.httpexceptions import HTTPException

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

    def __call__(self, value, system):
        """ Call the renderer implementation with the value
        and the system value passed in as arguments and return
        the result (a string or unicode object). The value is
        the return value of a view.  The system value is a
        dictionary containing available system values
        (e.g. view, context, and request). """

        request = system.get('request')
        if request:
            response = request.response
            ct = response.content_type
            if ct == response.default_content_type:
                response.content_type = 'application/json'

        # run after_calls on the value before jsonifying
        value = self.run_after_calls(value, system)
        view = system['view']
        enc_class = getattr(
            view, '_json_encoder', _JSONEncoder) or _JSONEncoder
        return json.dumps(value, cls=enc_class)

    def run_after_calls(self, value, system):
        request = system.get('request')
        if request and hasattr(request, 'action'):

            if request.action in ['index', 'show']:
                value = wrappers.wrap_in_dict(request)(result=value)

        return value


class DefaultResponseRendererMixin(object):
    def render_create(self, value, system):
        from nefertari.json_httpexceptions import JHTTPCreated
        request = system['request']
        kw = {
            'request': request,
            'resource': value,
        }
        if hasattr(value, 'to_dict'):
            kw['resource'] = value.to_dict()
            resource = system['view']._resource
            id_name = resource.id_name
            obj_id = getattr(value, value.pk_field())
            kw['location'] = request.route_url(
                resource.uid, **{id_name: obj_id})

        # TODO: Raising response rollbacks a transaction
        raise JHTTPCreated(**kw)

    def render_default_response(self, value, system):
        if not isinstance(value, HTTPException):
            method_name = 'render_{}'.format(system['request'].action)
            method = getattr(self, method_name, None)
            if method is not None:
                value = method(value, system)
        return value


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

        return self.render_default_response(value, system)
