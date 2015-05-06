#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest

import pytest
from mock import Mock, patch
from pyramid.testing import DummyRequest

from nefertari import wrappers
from nefertari.utils import dictset


class TestWrappers(unittest.TestCase):

    def test_issequence(self):
        class A(object):
            def __init__(self, *args):
                for arg in args:
                    setattr(self, arg, lambda x: x)

        assert not wrappers.issequence(A('strip'))
        assert not wrappers.issequence(A('foo'))
        assert wrappers.issequence(A('__getitem__'))
        assert wrappers.issequence(A('__iter__'))
        assert wrappers.issequence(A('__iter__', 'foo'))
        assert wrappers.issequence(A('__getitem__', 'foo'))

    def test_wrap_me_init(self):
        wrap = wrappers.wrap_me(before='foo', after=['bar'])
        assert wrap.before == ['foo']
        assert wrap.after == ['bar']

        wrap = wrappers.wrap_me(after=['bar'])
        assert wrap.before == []
        assert wrap.after == ['bar']

        wrap = wrappers.wrap_me()
        assert wrap.before == []
        assert wrap.after == []

    def test_wrap_me_call(self):
        meth = lambda x: x
        wrap = wrappers.wrap_me(before=['foo'], after=['bar'])
        assert not hasattr(meth, '_before_calls')
        assert not hasattr(meth, '_after_calls')
        wrap(meth)
        assert meth._before_calls == ['foo']
        assert meth._after_calls == ['bar']

        wrap(meth)
        assert meth._before_calls == ['foo', 'foo']
        assert meth._after_calls == ['bar', 'bar']

    def test_callable_base(self):
        class A(wrappers.callable_base):
            pass

        obj1 = A(id=1)
        obj2 = A(id=2)
        assert obj1 == obj2
        assert obj1.kwargs == {'id': 1}
        assert obj2.kwargs == {'id': 2}

    def test_obj2dict_dict_result(self):
        assert wrappers.obj2dict(None)(result={'a': 'b'}) == {'a': 'b'}

    def test_obj2dict_regular(self):
        result = Mock()
        result.to_dict.return_value = {'a': 1}
        assert wrappers.obj2dict(None)(result=result) == {'a': 1}

    def test_obj2dict_list_from_todict(self):
        result = Mock()
        result.to_dict.return_value = [dict(a=1), dict(b=2)]
        self.assertEqual(
            [dict(a=1), dict(b=2)],
            wrappers.obj2dict(request=None)(result=result))

    def test_obj2dict_nested(self):
        special = Mock()
        special.to_dict.return_value = {'special': 'dict'}
        result = [special]
        self.assertEqual(
            [{'special': 'dict'}],
            wrappers.obj2dict(request=None)(result=result))

    def test_obj2dict_other_type(self):
        self.assertEqual(
            'foo',
            wrappers.obj2dict(request=None)(result='foo'))

    def test_add_meta(self):
        result = {'data': [{'id': 4}]}
        request = DummyRequest(path='http://example.com', environ={})
        result = wrappers.add_meta(request=request)(result=result)
        assert result['count'] == 1
        assert result['data'][0]['self'] == 'http://example.com/4'

        environ = {'QUERY_STRING': '_limit=100'}
        request = DummyRequest(path='http://example.com?_limit=100',
                               environ=environ)
        assert request.path == 'http://example.com?_limit=100'
        result = wrappers.add_meta(request=request)(result=result)
        assert result['count'] == 1
        assert result['data'][0]['self'] == 'http://example.com/4'

    @patch('nefertari.wrappers.urllib')
    def test_add_meta_type_error(self, mock_lib):
        mock_lib.quote.side_effect = TypeError
        result = {'data': [{'id': 4}]}
        request = DummyRequest(path='http://example.com', environ={})
        result = wrappers.add_meta(request=request)(result=result)
        assert result['count'] == 1
        assert result['data'][0] == {'id': 4}

    def test_apply_privacy_no_data(self):
        assert wrappers.apply_privacy(None)(result={}) == {}

    @patch('nefertari.wrappers.engine')
    def test_apply_privacy_item_non_auth(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=['id'])
        mock_eng.get_document_cls.return_value = document_cls
        request = Mock(user=None)
        filtered = wrappers.apply_privacy(request)(result=dictset({
            '_type': 'foo',
            'self': 'http://example.com/1',
            'name': 'User1',
            'desc': 'User 1 data',
            'id': 1,
            'other_field': 123
        }))
        assert list(sorted(filtered.keys())) == [
            '_type', 'desc', 'name', 'self']

    @patch('nefertari.wrappers.engine')
    def test_apply_privacy_item_no_request(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=['id'])
        mock_eng.get_document_cls.return_value = document_cls
        filtered = wrappers.apply_privacy(None)(result=dictset({
            '_type': 'foo',
            'self': 'http://example.com/1',
            'name': 'User1',
            'desc': 'User 1 data',
            'id': 1,
            'other_field': 123
        }))
        assert list(sorted(filtered.keys())) == [
            '_type', 'desc', 'id', 'name', 'other_field', 'self']

    @patch('nefertari.wrappers.engine')
    def test_apply_privacy_item_auth(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=['id'])
        mock_eng.get_document_cls.return_value = document_cls
        request = Mock(user=Mock())
        filtered = wrappers.apply_privacy(request)(result=dictset({
            '_type': 'foo',
            'self': 'http://example.com/1',
            'name': 'User1',
            'desc': 'User 1 data',
            'id': 1,
            'other_field': 123
        }), is_admin=False)
        assert list(sorted(filtered.keys())) == [
            '_type', 'id', 'self']

    @patch('nefertari.wrappers.engine')
    def test_apply_privacy_item_auth_calculated(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=['id'])
        mock_eng.get_document_cls.return_value = document_cls

        class User(object):
            @classmethod
            def is_admin(self, obj):
                return False

        request = Mock(user=User())
        filtered = wrappers.apply_privacy(request)(result=dictset({
            '_type': 'foo',
            'self': 'http://example.com/1',
            'name': 'User1',
            'desc': 'User 1 data',
            'id': 1,
            'other_field': 123
        }))
        assert list(sorted(filtered.keys())) == [
            '_type', 'id', 'self']

    @patch('nefertari.wrappers.engine')
    def test_apply_privacy_item_admin(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=['id'])
        mock_eng.get_document_cls.return_value = document_cls
        request = Mock(user=Mock())
        filtered = wrappers.apply_privacy(request)(result=dictset({
            '_type': 'foo',
            'self': 'http://example.com/1',
            'name': 'User1',
            'desc': 'User 1 data',
            'id': 1,
            'other_field': 123
        }), is_admin=True)
        assert list(sorted(filtered.keys())) == [
            '_type', 'desc', 'id', 'name', 'other_field', 'self']
        filtered['_type'] == 'foo'
        filtered['desc'] == 'User 1 data'
        filtered['id'] == 1
        filtered['name'] == 'User1'
        filtered['other_field'] == 123
        filtered['self'] == 'http://example.com/1'
        mock_eng.get_document_cls.assert_called_once_with('foo')

    @patch('nefertari.wrappers.engine')
    def test_apply_privacy_item_admin_calculated(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=['id'])
        mock_eng.get_document_cls.return_value = document_cls

        class User(object):
            @classmethod
            def is_admin(self, obj):
                return True

        request = Mock(user=User())
        filtered = wrappers.apply_privacy(request)(result=dictset({
            '_type': 'foo',
            'self': 'http://example.com/1',
            'name': 'User1',
            'desc': 'User 1 data',
            'id': 1,
            'other_field': 123
        }))
        assert list(sorted(filtered.keys())) == [
            '_type', 'desc', 'id', 'name', 'other_field', 'self']
        filtered['_type'] == 'foo'
        filtered['desc'] == 'User 1 data'
        filtered['id'] == 1
        filtered['name'] == 'User1'
        filtered['other_field'] == 123
        filtered['self'] == 'http://example.com/1'
        mock_eng.get_document_cls.assert_called_once_with('foo')

    @patch('nefertari.wrappers.engine')
    def test_apply_privacy_item_no_document_cls(self, mock_eng):
        mock_eng.get_document_cls.side_effect = ValueError
        request = Mock(user=Mock())
        filtered = wrappers.apply_privacy(request)(result=dictset({
            '_type': 'foo',
            'self': 'http://example.com/1',
            'name': 'User1',
            'desc': 'User 1 data',
            'id': 1,
            'other_field': 123
        }), is_admin=True)
        assert list(sorted(filtered.keys())) == [
            '_type', 'desc', 'id', 'name', 'other_field', 'self']

    @patch('nefertari.wrappers.engine')
    def test_apply_privacy_item_no_fields(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=[])
        mock_eng.get_document_cls.return_value = document_cls
        request = Mock(user=Mock())
        filtered = wrappers.apply_privacy(request)(result=dictset({
            '_type': 'foo',
            'self': 'http://example.com/1',
            'name': 'User1',
            'desc': 'User 1 data',
            'id': 1,
            'other_field': 123
        }), is_admin=False)
        assert list(sorted(filtered.keys())) == ['_type', 'self']

    @patch('nefertari.wrappers.engine')
    def test_apply_privacy_collection(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=['id'])
        mock_eng.get_document_cls.return_value = document_cls
        request = Mock(user=Mock())
        result = {
            'total': 1,
            'count': 1,
            'data': [dictset({
                '_type': 'foo',
                'self': 'http://example.com/1',
                'name': 'User1',
                'desc': 'User 1 data',
                'id': 1,
                'other_field': 123
            })]
        }
        filtered = wrappers.apply_privacy(request)(
            result=result, is_admin=False)
        assert list(sorted(filtered.keys())) == ['count', 'data', 'total']
        assert len(filtered['data']) == 1
        data = filtered['data'][0]
        assert list(sorted(data.keys())) == ['_type', 'id', 'self']

    @patch('nefertari.wrappers.obj2dict')
    def test_wrap_in_dict_no_meta_dict(self, mock_obj):
        result = Mock(spec=[])
        mock_obj.return_value = lambda **kw: {'foo': 'bar'}
        processed = wrappers.wrap_in_dict(123)(result=result, qoo=1)
        mock_obj.assert_called_once_with(123)
        assert processed == {'foo': 'bar'}

    @patch('nefertari.wrappers.obj2dict')
    def test_wrap_in_dict_meta_dict(self, mock_obj):
        mock_obj.return_value = lambda **kw: {'foo': 'bar'}
        result = Mock(_nefertari_meta={'meta': 'metameta'})
        processed = wrappers.wrap_in_dict(123)(result=result, qoo=1)
        mock_obj.assert_called_once_with(123)
        assert processed == {'foo': 'bar'}

    @patch('nefertari.wrappers.obj2dict')
    def test_wrap_in_dict_no_meta_list(self, mock_obj):
        result = Mock(spec=[])
        mock_obj.return_value = lambda **kw: [{'foo': 'bar'}]
        processed = wrappers.wrap_in_dict(123)(result=result, qoo=1)
        mock_obj.assert_called_once_with(123)
        assert processed == {'data': [{'foo': 'bar'}]}

    @patch('nefertari.wrappers.obj2dict')
    def test_wrap_in_dict_meta_list(self, mock_obj):
        mock_obj.return_value = lambda **kw: [{'foo': 'bar'}]
        result = Mock()
        result._nefertari_meta = {'meta': 'metameta'}
        processed = wrappers.wrap_in_dict(123)(result=result, qoo=1)
        mock_obj.assert_called_once_with(123)
        assert processed == {'data': [{'foo': 'bar'}], 'meta': 'metameta'}

    @patch('nefertari.wrappers.engine')
    def test_add_confirmation_url(self, mock_eng):
        mock_eng.BaseDocument.count.return_value = 12321
        request = Mock(
            url='http://example.com/api?foo=bar',
            params={'foo': 'bar'},
            method='GET'
        )
        result = wrappers.add_confirmation_url(request)(result=3)
        assert result['method'] == 'GET'
        assert result['count'] == 12321
        assert result['confirmation_url'] == (
            'http://example.com/api?foo=bar&__confirmation&_m=GET')

    @patch('nefertari.wrappers.engine')
    def test_add_confirmation_url_no_request_params(self, mock_eng):
        mock_eng.BaseDocument.count.return_value = 12321
        request = Mock(
            url='http://example.com/api',
            params=None,
            method='GET'
        )
        result = wrappers.add_confirmation_url(request)(result=3)
        assert result['method'] == 'GET'
        assert result['count'] == 12321
        assert result['confirmation_url'] == (
            'http://example.com/api?__confirmation&_m=GET')

    def test_add_etag_no_data(self):
        wrapper = wrappers.add_etag(Mock())
        wrapper.request.response.etag = None
        wrapper(result={'data': []})
        assert wrapper.request.response.etag is None
        wrapper(result={})
        assert wrapper.request.response.etag is None

    def test_add_etag(self):
        wrapper = wrappers.add_etag(Mock())
        wrapper.request.response.etag = None
        wrapper(result={'data': [
            {'id': 1, '_version': 1},
            {'id': 2, '_version': 1},
        ]})
        expected1 = '20d135f0f28185b84a4cf7aa51f29500'
        assert wrapper.request.response.etag == expected1

        # Etag is the same when data isn't changed
        wrapper(result={'data': [
            {'id': 1, '_version': 1},
            {'id': 2, '_version': 1},
        ]})
        assert isinstance(wrapper.request.response.etag, basestring)
        assert wrapper.request.response.etag == expected1

        # New object added
        wrapper(result={'data': [
            {'id': 1, '_version': 1},
            {'id': 2, '_version': 1},
            {'id': 3, '_version': 1},
        ]})
        assert isinstance(wrapper.request.response.etag, basestring)
        assert wrapper.request.response.etag != expected1

        # Existing object's version changed
        wrapper(result={'data': [
            {'id': 1, '_version': 1},
            {'id': 2, '_version': 2},
        ]})
        assert isinstance(wrapper.request.response.etag, basestring)
        assert wrapper.request.response.etag != expected1

    def test_set_total(self):
        result = Mock(_nefertari_meta={'total': 5})
        processed = wrappers.set_total(None, 2)(result=result)
        assert processed._nefertari_meta['total'] == 2

        result = Mock(_nefertari_meta={'total': 1})
        processed = wrappers.set_total(None, 2)(result=result)
        assert processed._nefertari_meta['total'] == 1

    def test_set_total_no_meta(self):
        result = Mock(spec=[])
        processed = wrappers.set_total(None, 2)(result=result)
        assert not hasattr(processed, '_nefertari_meta')

    @patch('nefertari.wrappers.set_total')
    def test_set_public_limits(self, mock_set):
        request = Mock()
        request.registry.settings = {'public_max_limit': 123}
        view = Mock(
            request=request,
            _params={'_limit': 100, '_page': 1, '_start': 90})
        wrappers.set_public_limits(view)
        mock_set.assert_called_once_with(view.request, total=123)
        view.add_after_call.assert_called_once_with(
            'index', mock_set(), pos=0)
        assert view._params['_limit'] == 33

    @patch('nefertari.wrappers.set_total')
    def test_set_public_limits_no_params(self, mock_set):
        request = Mock()
        request.registry.settings = {}
        view = Mock(request=request, _params={})
        wrappers.set_public_limits(view)
        mock_set.assert_called_once_with(view.request, total=100)
        view.add_after_call.assert_called_once_with(
            'index', mock_set(), pos=0)
        assert '_limit' not in view._params

    @patch('nefertari.wrappers.set_total')
    def test_set_public_limits_value_err(self, mock_set):
        from nefertari.json_httpexceptions import JHTTPBadRequest
        request = Mock()
        request.registry.settings = {}
        view = Mock(request=request, _params={})
        mock_set.side_effect = ValueError
        with pytest.raises(JHTTPBadRequest):
            wrappers.set_public_limits(view)
