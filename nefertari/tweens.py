import time
from pyramid.settings import asbool
import logging
import json

log = logging.getLogger(__name__)


def request_timing(handler, registry):
    threshold = float(registry.settings.get(
        'request_timing.slow_request_threshold', 2))
    log.info('request_timing enabled: slow_request_threshold = %s' % threshold)

    def timing(request):

        start = time.time()
        try:
            return handler(request)
        finally:
            delta = time.time()-start
            msg = '%s (%s) request took %s seconds' % (
                request.method, request.url, delta)
            if delta > threshold:
                log.warning(msg)
            else:
                log.debug(msg)

    return timing


def post_tunneling(handler, registry):
    """Allow other request methods to be tunneled via POST.

    This allows PUT, PATCH and DELETE requests to be tunneled via POST requests.
    The method can be specified using a parameter or a header...

    The name of the parameter is '_method'; it can be a query or POST
    parameter. The query parameter will be preferred if both the query and
    POST parameters are present in the request.

    The name of the header is 'X-HTTP-Method-Override'. If the parameter
    described above is passed, this will be ignored.

    The request method will be overwritten before it reaches application
    code, such that the application will never be aware of the original
    request method. Likewise, the parameter and header will be removed from
    the request, and the application will never see them.

    """
    log.info('post_tunneling enabled')

    param_name = '_method'
    header_name = 'X-HTTP-Method-Override'
    allowed_methods = set(['PUT', 'DELETE', 'PATCH'])
    disallowed_message = (
        'Only these methods may be tunneled over POST: {0}.'
        .format(sorted(list(allowed_methods))))

    def post_tunneling(request):
        if request.method == 'POST':
            method = ''

            if param_name in request.GET:
                method = request.GET[param_name]
            elif param_name in request.POST:
                method = request.POST[param_name]
            elif header_name in request.headers:
                method = request.headers[header_name]

            if method in allowed_methods:
                request.GET.pop(param_name, None)
                request.POST.pop(param_name, None)
                request.headers.pop(header_name, None)
                request.method = method

        return handler(request)

    return post_tunneling


def get_tunneling(handler, registry):
    """
    This allows all methods to be tunneled via GET for dev/debuging purposes.
    """

    log.info('get_tunneling enabled')

    def get_tunneling(request):
        if request.method == 'GET':
            method = request.GET.pop('_m', 'GET')
            request.method = method

            if method in ['POST', 'PUT', 'PATCH']:
                request.body = json.dumps(request.GET.mixed())
                request.content_type = 'application/json'
                # request.POST.update(request.GET)

        return handler(request)

    return get_tunneling


def cors(handler, registry):
    log.info('cors_tunneling enabled')

    allow_origins = [
        each.strip() for each in
        registry.settings.get('cors.allow_origins', '').split(',')]
    allow_credentials = registry.settings.get('cors.allow_credentials', None)

    def cors(request):
        origin = request.headers.get('Origin') or request.host_url
        response = handler(request)

        if origin in allow_origins:
            response.headerlist.append(('Access-Control-Allow-Origin', origin))

        if allow_credentials is not None:
            response.headerlist.append(
                ('Access-Control-Allow-Credentials', allow_credentials))

        return response

    if not allow_origins:
        log.warning('cors.allow_origins is not set')
    else:
        log.info('Allow Origins = %s ' % allow_origins)

    if allow_credentials is None:
        log.warning('cors.allow_credentials is not set')

    elif asbool(allow_credentials) and allow_origins == '*':
        log.error('Not allowed Access-Control-Allow-Credentials '
                  'to set to TRUE if origin is *')
        return
    else:
        log.info('Access-Control-Allow-Credentials = %s ' % allow_credentials)

    return cors


def cache_control(handler, registry):
    log.info('cache_control enabled')

    def cache_control(request):
        response = handler(request)

        #change only if the header cache-control is missing
        add_header = True
        for header in response.headerlist:
            if 'Cache-Control' in header:
                add_header = False
        if add_header:
            response.cache_expires(0)

        return response

    return cache_control


def ssl(handler, registry):
    log.info('ssl enabled')

    def ssl(request):
        scheme = request.environ.get('HTTP_X_URL_SCHEME') \
            or request.environ.get('HTTP_X_FORWARDED_PROTO')

        if scheme:
            scheme = scheme.lower()
            log.debug('setting url_scheme to %s', scheme)
            request.scheme = request.environ['wsgi.url_scheme'] = scheme

        return handler(request)

    return ssl


from pyramid.events import ContextFound


def enable_selfalias(config, id_name):
    """
    This allows to replace id_name with "self".
    i.e. /users/joe/account == /users/self/account if joe is in the session
    as authorized user
    """

    def context_found_subscriber(event):
        request = event.request
        if (request.matchdict and
                request.matchdict.get(id_name, None) == 'self' and
                request.user):
            request.matchdict[id_name] = request.user.username

    config.add_subscriber(context_found_subscriber, ContextFound)
