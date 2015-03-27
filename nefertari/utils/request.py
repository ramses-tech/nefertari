import logging
import requests
import urllib
from pyramid.response import Response

from nefertari.utils.utils import json_dumps
from nefertari.json_httpexceptions import *

log = logging.getLogger(__name__)


def pyramid_resp(resp, **kw):
    return Response(status_code=resp.status_code,
                    headers=resp.headers,
                    body=resp.text, **kw)


class Requests(object):
    def __init__(self, base_url=''):
        self.base_url = base_url

    def prepare_url(self, path='', params={}):
        url = self.base_url

        if path:
            url = '%s%s' % (url, (path if path.startswith('/') else '/'+path))

        if params:
            url = '%s%s%s' % (url, '&' if '?' in url else '?',
                              urllib.urlencode(params))

        return url

    def get(self, path, params={}, **kw):
        url = self.prepare_url(path, params)
        log.debug('%s', url)

        try:
            resp = requests.get(url, **kw)
            if not resp.ok:
                raise exception_response(**resp.json())
            return resp.json()
        except requests.ConnectionError as e:
            raise JHTTPServerError('Server is down? %s' % e)

    def mget(self, path, params={}, page_size=None):
        total = params['_limit']
        start = params.get('_start', 0)
        params['_limit'] = page_size
        page_count = total/page_size

        for ix in range(page_count):
            params['_start'] = start + ix*page_size
            yield self.get(path, params)

        reminder = total % page_size
        if reminder:
            params['_start'] = start + page_count*page_size
            params['_limit'] = reminder
            yield self.get(path, params)

    def post(self, path='', data={}, **kw):
        url = self.prepare_url(path)
        log.debug('%s, kwargs:%.512s', url, data)
        try:
            resp = requests.post(
                url, data=json_dumps(data),
                headers={'content-type': 'application/json'},
                **kw)
            if not resp.ok:
                raise exception_response(**resp.json())

            return pyramid_resp(resp)
        except requests.ConnectionError as e:
            raise JHTTPServerError('Server is down? %s' % e)

    def mpost(self, path='', data={}, bulk_size=None, bulk_key=None):
        bulk_data = data[bulk_key]
        total = len(bulk_data)
        page_count = total/bulk_size

        for ix in range(page_count):
            data[bulk_key] = bulk_data[ix*bulk_size:(ix+1)*bulk_size]
            yield self.post(path, data)

        reminder = total % bulk_size
        if reminder:
            st = page_count*bulk_size
            data[bulk_key] = bulk_data[st:st+reminder]
            yield self.post(path, data)

    def put(self, path='', data={}, **kw):
        try:
            url = self.prepare_url(path)
            log.debug('%s, kwargs:%.512s', url, data)

            resp = requests.put(
                url, data=json_dumps(data),
                headers={'content-type': 'application/json'},
                **kw)
            if not resp.ok:
                raise exception_response(**resp.json())

            return resp.json()
        except requests.ConnectionError as e:
            raise JHTTPServerError('Server is down? %s' % e)

    def head(self, path='', params={}):
        try:
            resp = requests.head(self.prepare_url(path, params))
            if not resp.ok:
                raise exception_response(**resp.json())

        except requests.ConnectionError as e:
            raise JHTTPServerError('Server is down? %s' % e)

    def delete(self, path='', **kw):
        url = self.prepare_url(path)
        log.debug(url)
        try:
            resp = requests.delete(
                url, headers={'content-type': 'application/json'},
                **kw)
            if not resp.ok:
                raise exception_response(**resp.json())

            return resp.json()
        except requests.ConnectionError as e:
            raise JHTTPServerError('Server is down? %s' % e)
