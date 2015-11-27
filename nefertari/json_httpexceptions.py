import logging
import sys
import traceback
from datetime import datetime

import six
from pyramid import httpexceptions as http_exc

from nefertari.wrappers import apply_privacy


logger = logging.getLogger(__name__)


def includeme(config):
    config.add_view(view=httperrors, context=http_exc.HTTPError)
    logger.info('Include json_httpexceptions')


STATUS_MAP = dict()
BLACKLIST_LOG = [404]
BASE_ATTRS = ['status_code', 'explanation', 'message', 'title']


def add_stack():
    return ''.join(traceback.format_stack())


def create_json_response(obj, request=None, log_it=False, show_stack=False,
                         **extra):
    from nefertari.utils import json_dumps
    body = extra.pop('body', None)
    encoder = extra.pop('encoder', None)

    if body is None:
        body = dict()
        for attr in BASE_ATTRS:
            body[attr] = extra.pop(attr, None) or getattr(obj, attr, None)

        extra['timestamp'] = datetime.utcnow()
        if request:
            extra['request_url'] = request.url
            if obj.status_int in [403, 401]:
                extra['client_addr'] = request.client_addr
                extra['remote_addr'] = request.remote_addr

        if obj.location:
            body['_pk'] = obj.location.split('/')[-1]
        body.update(extra)

    obj.body = six.b(json_dumps(body, encoder=encoder))
    show_stack = log_it or show_stack
    status = obj.status_int

    if 400 <= status < 600 and status not in BLACKLIST_LOG or log_it:
        msg = '%s: %s' % (obj.status.upper(), obj.body)
        if obj.status_int in [400, 500] or show_stack:
            msg += '\nSTACK BEGIN>>\n%s\nSTACK END<<' % add_stack()

        logger.error(msg)

    obj.content_type = 'application/json'
    return obj


def exception_response(status_code, **kw):
    return STATUS_MAP[status_code](**kw)


class JBase(object):
    def __init__(self, *arg, **kw):
        from nefertari.utils import dictset
        kw = dictset(kw)
        self.__class__.__base__.__init__(
            self, *arg,
            **kw.subset(BASE_ATTRS+['headers', 'location']))

        create_json_response(self, **kw)


thismodule = sys.modules[__name__]


http_exceptions = list(http_exc.status_map.values()) + [
    http_exc.HTTPBadRequest,
    http_exc.HTTPInternalServerError,
]


for exc_cls in http_exceptions:
    name = "J%s" % exc_cls.__name__
    STATUS_MAP[exc_cls.code] = type(name, (JBase, exc_cls), {})
    setattr(thismodule, name, STATUS_MAP[exc_cls.code])


def httperrors(context, request):
    return create_json_response(context, request=request)


class JHTTPCreated(http_exc.HTTPCreated):
    def __init__(self, *args, **kwargs):
        resource = kwargs.pop('resource', None)
        resp_kwargs = {
            'obj': self,
            'request': kwargs.pop('request', None),
            'encoder': kwargs.pop('encoder', None),
            'body': kwargs.pop('body', None),
            'resource': resource,
        }
        super(JHTTPCreated, self).__init__(*args, **kwargs)

        if resource and 'location' in kwargs:
            resource['_self'] = kwargs['location']

        create_json_response(**resp_kwargs)
