import pytest
from mock import Mock, patch, call
from pyramid.response import Response
import requests

from nefertari.utils import request
from nefertari import json_httpexceptions as jexc


class TestRequestHelpers(object):

    def test_pyramid_resp(self):
        resp = Mock(
            status_code=200, headers=[('Foo', 'bar')],
            text='success response')
        pyramid_resp = request.pyramid_resp(resp)
        assert isinstance(pyramid_resp, Response)
        assert pyramid_resp.status_code == 200
        assert 'Foo' in pyramid_resp.headers
        assert pyramid_resp.body == 'success response'


class TestRequestsClass(object):

    def test_prepare_url(self):
        req = request.Requests(base_url='http://example.com')
        url = req.prepare_url(path='/api', params={'foo': 'bar'})
        assert url == 'http://example.com/api?foo=bar'

    def test_prepare_url_no_params(self):
        req = request.Requests(base_url='http://example.com')
        url = req.prepare_url(path='/api')
        assert url == 'http://example.com/api'

    def test_prepare_url_no_path(self):
        req = request.Requests(base_url='http://example.com')
        url = req.prepare_url(params={'foo': 'bar'})
        assert url == 'http://example.com?foo=bar'

    @patch('nefertari.utils.request.requests.get')
    def test_get(self, mock_meth):
        req = request.Requests(base_url='http://example.com')
        get_resp = Mock(ok=True)
        get_resp.json.return_value = {}
        mock_meth.return_value = get_resp
        resp = req.get(path='/api', params={'foo': 'bar'}, a=1)
        mock_meth.assert_called_once_with(
            'http://example.com/api?foo=bar', a=1)
        assert resp == mock_meth().json()

    @patch('nefertari.utils.request.requests.get')
    def test_get_not_ok(self, mock_meth):
        req = request.Requests(base_url='http://example.com')
        get_resp = Mock(ok=False)
        get_resp.json.return_value = {'status_code': 400}
        mock_meth.return_value = get_resp
        with pytest.raises(jexc.JHTTPBadRequest):
            req.get(path='/api')

    @patch('nefertari.utils.request.requests.get')
    def test_get_connection_error(self, mock_meth):
        req = request.Requests(base_url='http://example.com')
        mock_meth.side_effect = requests.ConnectionError
        with pytest.raises(jexc.JHTTPServerError):
            req.get(path='/api')

    # @patch('nefertari.utils.request.Requests.get')
    # def test_mget(self, mock_meth):
    #     req = request.Requests(base_url='http://example.com')
    #     responses = [
    #         r for r in req.mget(
    #             path='/api',
    #             params={'foo': 'bar', '_limit': 7},
    #             page_size=2)]
    #     assert mock_meth.call_count == 4
    #     mock_meth.assert_has_calls([
    #         call('/api', {'_start': 0, '_limit': 2, 'foo': 'bar'}),
    #         call('/api', {'_start': 2, '_limit': 4, 'foo': 'bar'}),
    #         call('/api', {'_start': 4, '_limit': 6, 'foo': 'bar'}),
    #         call('/api', {'_start': 6, '_limit': 1, 'foo': 'bar'}),
    #     ])
