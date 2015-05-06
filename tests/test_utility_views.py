from mock import Mock

from nefertari import utility_views as uviews
from nefertari.json_httpexceptions import *


class TestOptionsView(object):
    header_str = 'HEAD, TRACE, GET, PATCH, PUT, POST, OPTIONS, DELETE'

    def test_call_methods_header(self):
        response = Mock(headers={})
        request = Mock(
            headers={'Access-Control-Request-Method': ''},
            response=response)
        resp = uviews.OptionsView(request=request)()
        assert resp is response
        assert response.headers == {
            'Allow': self.header_str,
            'Access-Control-Allow-Methods': self.header_str,
        }

    def test_call_headers_header(self):
        response = Mock(headers={})
        request = Mock(
            headers={'Access-Control-Request-Headers': ''},
            response=response)
        resp = uviews.OptionsView(request=request)()
        assert resp is response
        assert response.headers == {
            'Allow': self.header_str,
            'Access-Control-Allow-Headers': 'origin, x-requested-with, content-type',
        }

    def test_call_no_headers(self):
        response = Mock(headers={})
        request = Mock(
            headers={},
            response=response)
        resp = uviews.OptionsView(request=request)()
        assert resp is response
        assert response.headers == {
            'Allow': self.header_str,
        }
