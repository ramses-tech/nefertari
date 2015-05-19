from pyramid.view import view_config


@view_config(name='options_view', request_method='OPTIONS',
             route_name='options')
class OptionsView(object):
    all_methods = set(['GET', 'HEAD', 'POST', 'OPTIONS', 'PUT', 'DELETE',
                       'PATCH', 'TRACE'])

    def __init__(self, request):
        self.request = request

    def __call__(self):
        request = self.request

        request.response.headers['Allow'] = ', '.join(self.all_methods)

        if 'Access-Control-Request-Method' in request.headers:
            request.response.headers['Access-Control-Allow-Methods'] = \
                ', '.join(self.all_methods)

        if 'Access-Control-Request-Headers' in request.headers:
            request.response.headers['Access-Control-Allow-Headers'] = \
                'origin, x-requested-with, content-type'

        return request.response
