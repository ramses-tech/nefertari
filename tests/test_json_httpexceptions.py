import json

import pytest
import six
from mock import Mock, patch

from nefertari import json_httpexceptions as jsonex
from nefertari.renderers import _JSONEncoder


class TestJSONHTTPExceptionsModule(object):

    def test_includeme(self):
        config = Mock()
        jsonex.includeme(config)
        config.add_view.assert_called_once_with(
            view=jsonex.httperrors,
            context=jsonex.http_exc.HTTPError)

    @patch.object(jsonex, 'traceback')
    def test_add_stack(self, mock_trace):
        mock_trace.format_stack.return_value = ['foo', 'bar']
        assert jsonex.add_stack() == 'foobar'

    def test_create_json_response(self):
        request = Mock(
            url='http://example.com',
            client_addr='127.0.0.1',
            remote_addr='127.0.0.2')
        obj = Mock(
            status_int=401,
            location='http://example.com/api')
        obj2 = jsonex.create_json_response(
            obj, request, encoder=_JSONEncoder,
            status_code=402, explanation='success',
            message='foo', title='bar')
        assert obj2.content_type == 'application/json'
        assert isinstance(obj2.body, six.binary_type)
        body = json.loads(obj2.body.decode('utf-8'))
        assert sorted(body.keys()) == [
            '_pk', 'client_addr', 'explanation', 'message', 'remote_addr',
            'request_url', 'status_code', 'timestamp', 'title'
        ]
        assert body['remote_addr'] == '127.0.0.2'
        assert body['client_addr'] == '127.0.0.1'
        assert body['status_code'] == 402
        assert body['explanation'] == 'success'
        assert body['title'] == 'bar'
        assert body['message'] == 'foo'
        assert body['_pk'] == 'api'
        assert body['request_url'] == 'http://example.com'

    @patch.object(jsonex, 'add_stack')
    def test_create_json_response_obj_properties(self, mock_stack):
        mock_stack.return_value = 'foo'
        obj = Mock(
            status_int=401,
            location='http://example.com/api',
            status_code=402, explanation='success',
            message='foo', title='bar')
        obj2 = jsonex.create_json_response(
            obj, None, encoder=_JSONEncoder)
        body = json.loads(obj2.body.decode('utf-8'))
        assert body['status_code'] == 402
        assert body['explanation'] == 'success'
        assert body['title'] == 'bar'
        assert body['message'] == 'foo'
        assert body['_pk'] == 'api'

    @patch.object(jsonex, 'add_stack')
    def test_create_json_response_stack_calls(self, mock_stack):
        mock_stack.return_value = 'foo'
        obj = Mock(status_int=401, location='http://example.com/api')
        jsonex.create_json_response(obj, None, encoder=_JSONEncoder)
        assert mock_stack.call_count == 0

        obj = Mock(status_int=500, location='http://example.com/api')
        jsonex.create_json_response(obj, None, encoder=_JSONEncoder)
        mock_stack.assert_called_with()
        assert mock_stack.call_count == 1

        obj = Mock(status_int=401, location='http://example.com/api')
        jsonex.create_json_response(
            obj, None, encoder=_JSONEncoder, show_stack=True)
        mock_stack.assert_called_with()
        assert mock_stack.call_count == 2

        obj = Mock(status_int=401, location='http://example.com/api')
        jsonex.create_json_response(
            obj, None, encoder=_JSONEncoder, log_it=True)
        mock_stack.assert_called_with()
        assert mock_stack.call_count == 3

    def test_create_json_response_with_body(self):
        obj = Mock(
            status_int=401,
            location='http://example.com/api')
        obj2 = jsonex.create_json_response(
            obj, None, encoder=_JSONEncoder,
            status_code=402, explanation='success',
            message='foo', title='bar', body={'zoo': 'zoo'})
        assert obj2.content_type == 'application/json'
        assert isinstance(obj2.body, six.binary_type)
        body = json.loads(obj2.body.decode('utf-8'))
        assert body == {'zoo': 'zoo'}

    def test_exception_response(self):
        jsonex.STATUS_MAP[12345] = lambda x: x + 3
        assert jsonex.exception_response(12345, x=1) == 4
        with pytest.raises(KeyError):
            jsonex.exception_response(3123123123123123)
        jsonex.STATUS_MAP.pop(12345, None)

    def test_status_map(self):
        codes = [
            200, 201, 202, 203, 204, 205, 206,
            300, 301, 302, 303, 304, 305, 307,
            400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410,
            411, 412, 413, 414, 415, 416, 417, 422, 423, 424,
            500, 501, 502, 503, 504, 505, 507
        ]
        for code in codes:
            assert code in jsonex.STATUS_MAP
        for code_exc in jsonex.STATUS_MAP.values():
            assert hasattr(jsonex, code_exc.__name__)

    @patch.object(jsonex, 'create_json_response')
    def test_httperrors(self, mock_create):
        jsonex.httperrors({'foo': 'bar'}, 1)
        mock_create.assert_called_once_with({'foo': 'bar'}, request=1)

    @patch.object(jsonex, 'create_json_response')
    def test_jhttpcreated(self, mock_create):
        resp = jsonex.JHTTPCreated(
            resource={'foo': 'bar'},
            location='http://example.com/1',
            encoder=1)
        mock_create.assert_called_once_with(
            obj=resp, resource={'foo': 'bar', '_self': 'http://example.com/1'},
            request=None, encoder=1, body=None)
