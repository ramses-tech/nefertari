import time
import logging
import json

import six
from pyramid.settings import asbool
from nefertari.utils import drop_reserved_params

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
            delta = time.time() - start
            msg = '%s (%s) request took %s seconds' % (
                request.method, request.url, delta)
            if delta > threshold:
                log.warning(msg)
            else:
                log.debug(msg)

    return timing


def get_tunneling(handler, registry):
    """ Allows all methods to be tunneled via GET for dev/debuging
    purposes.
    """
    log.info('get_tunneling enabled')

    def get_tunneling(request):
        if request.method == 'GET':
            method = request.GET.pop('_m', 'GET')
            request.method = method

            if method in ['POST', 'PUT', 'PATCH']:
                get_params = request.GET.mixed()
                valid_params = drop_reserved_params(get_params)
                request.body = six.b(json.dumps(valid_params))
                request.content_type = 'application/json'
                request._tunneled_get = True

        return handler(request)

    return get_tunneling


def cors(handler, registry):
    log.info('cors_tunneling enabled')

    allow_origins_setting = registry.settings.get(
        'cors.allow_origins', '').strip()

    allow_origins = [
        each.strip() for each in allow_origins_setting.split(',')]
    allow_credentials = registry.settings.get('cors.allow_credentials', None)

    def cors(request):
        origin = request.headers.get('Origin') or request.host_url
        response = handler(request)

        if origin in allow_origins or '*' in allow_origins:
            response.headerlist.append(('Access-Control-Allow-Origin', origin))

        if allow_credentials is not None:
            response.headerlist.append(
                ('Access-Control-Allow-Credentials', allow_credentials))

        return response

    if not allow_origins_setting:
        log.warning('cors.allow_origins is not set')
    else:
        log.info('Allow Origins = %s ' % allow_origins)

    if allow_credentials is None:
        log.warning('cors.allow_credentials is not set')

    elif asbool(allow_credentials) and allow_origins_setting == '*':
        raise Exception('Not allowed Access-Control-Allow-Credentials '
                        'to set to TRUE if origin is *')
    else:
        log.info('Access-Control-Allow-Credentials = %s ' % allow_credentials)

    return cors


def cache_control(handler, registry):
    log.info('cache_control enabled')

    def cache_control(request):
        response = handler(request)

        # change only if the header cache-control is missing
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
    This allows replacing id_name with "self".
    e.g. /users/joe/account == /users/self/account if joe is in the session
    as an authorized user
    """

    def context_found_subscriber(event):
        request = event.request
        user = getattr(request, 'user', None)
        if (request.matchdict and
                request.matchdict.get(id_name, None) == 'self' and
                user):
            request.matchdict[id_name] = user.username

    config.add_subscriber(context_found_subscriber, ContextFound)
