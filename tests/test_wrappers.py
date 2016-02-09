#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest

import pytest
import six
from mock import Mock, patch
from pyramid.testing import DummyRequest

from nefertari import wrappers
from nefertari.utils import dictset
from nefertari.json_httpexceptions import JHTTPForbidden


class TestWrappers(unittest.TestCase):
    model_test_data = dictset({
        '_pk': '1',
        '_type': 'foo',
        '_self': 'http://example.com/1',
        'name': 'User1',
        'desc': 'User 1 data',
        'id': 1,
        'other_field': 123
    })

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

        environ = {'QUERY_STRING': '_limit=100'}
        request = DummyRequest(path='http://example.com?_limit=100',
                               environ=environ)
        assert request.path == 'http://example.com?_limit=100'
        result = wrappers.add_meta(request=request)(result=result)
        assert result['count'] == 1

    def test_add_meta_type_error(self):
        result = {'data': [{'id': 4}]}
        request = DummyRequest(path='http://example.com', environ={})
        result = wrappers.add_meta(request=request)(result=result)
        assert result['count'] == 1
        assert result['data'][0] == {'id': 4}

    def test_add_object_url_collection_not_found_resource(self):
        result = {'data': [{'_pk': 4, '_type': 'User'}]}
        environ = {'QUERY_STRING': '_limit=100'}
        request = DummyRequest(path='http://example.com', environ=environ)
        wrapper = wrappers.add_object_url(request=request)
        wrapper.model_collections = {'Story': 123}
        result = wrapper(result=result)
        assert result['data'][0]['_self'] == 'http://example.com'

    def test_add_object_url_collection_no_type(self):
        result = {'data': [{'_pk': 4}]}
        request = DummyRequest(path='http://example.com', environ={})
        wrapper = wrappers.add_object_url(request=request)
        wrapper.model_collections = {'Story': 123}
        result = wrapper(result=result)
        assert '_self' not in result['data'][0]

    def test_add_object_url_collection(self):
        result = {'data': [{'_pk': 4, '_type': 'Story'}]}
        request = Mock(matchdict=None)
        wrapper = wrappers.add_object_url(request=request)
        wrapper.model_collections = {
            'Story': Mock(uid='stories_resource', id_name='story_id'),
        }
        result = wrapper(result=result)
        request.route_url.assert_called_once_with(
            'stories_resource', story_id=4)
        assert result['data'][0]['_self'] == request.route_url()

    def test_add_object_url_item(self):
        result = {'_pk': 4, '_type': 'Story'}
        request = Mock(matchdict=None)
        wrapper = wrappers.add_object_url(request=request)
        wrapper.model_collections = {
            'Story': Mock(uid='stories_resource', id_name='story_id'),
        }
        result = wrapper(result=result)
        request.route_url.assert_called_once_with(
            'stories_resource', story_id=4)
        assert result['_self'] == request.route_url()

    def test_add_object_url_with_parent(self):
        result = {'_pk': 4, '_type': 'Story'}
        request = Mock(matchdict={'user_username': 'admin'})
        wrapper = wrappers.add_object_url(request=request)
        wrapper.model_collections = {
            'Story': Mock(uid='stories_resource', id_name='story_id'),
        }
        result = wrapper(result=result)
        request.route_url.assert_called_once_with(
            'stories_resource', user_username='admin', story_id=4)
        assert result['_self'] == request.route_url()

    @patch('nefertari.utils.validate_data_privacy')
    def test_apply_request_privacy_valid(self, mock_validate):
        wrapper = wrappers.apply_request_privacy(
            Mock(__name__='Foo'), {'zoo': 1})
        try:
            wrapper(request=4)
        except Exception:
            raise Exception('Unexpected error')
        mock_validate.assert_called_once_with(
            4, {'zoo': 1, '_type': 'Foo'},
            wrapper_kw={'drop_hidden': False})

    @patch('nefertari.utils.validate_data_privacy')
    def test_apply_request_privacy_invalid(self, mock_validate):
        mock_validate.side_effect = wrappers.ValidationError('boo')
        wrapper = wrappers.apply_request_privacy(
            Mock(__name__='Foo'), {'zoo': 1})
        with pytest.raises(JHTTPForbidden) as ex:
            wrapper(request=4)
        expected = 'Not enough permissions to update fields: boo'
        assert str(ex.value) == expected
        mock_validate.assert_called_once_with(
            4, {'zoo': 1, '_type': 'Foo'},
            wrapper_kw={'drop_hidden': False})

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
        result = wrappers.add_confirmation_url(request)(result={})
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
        result = wrappers.add_confirmation_url(request)(result={})
        assert result['method'] == 'GET'
        assert result['count'] == 12321
        assert result['confirmation_url'] == (
            'http://example.com/api?__confirmation&_m=GET')

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
            _query_params={'_limit': 100, '_page': 1, '_start': 90})
        wrappers.set_public_limits(view)
        mock_set.assert_called_once_with(view.request, total=123)
        view.add_after_call.assert_called_once_with(
            'index', mock_set(), pos=0)
        assert view._query_params['_limit'] == 33

    @patch('nefertari.wrappers.set_total')
    def test_set_public_limits_no_params(self, mock_set):
        request = Mock()
        request.registry.settings = {}
        view = Mock(request=request, _query_params={})
        wrappers.set_public_limits(view)
        mock_set.assert_called_once_with(view.request, total=100)
        view.add_after_call.assert_called_once_with(
            'index', mock_set(), pos=0)
        assert '_limit' not in view._query_params

    def test_set_public_limits_value_err(self):
        from nefertari.json_httpexceptions import JHTTPBadRequest
        request = Mock()
        request.registry.settings = {}
        view = Mock(request=request, _query_params={})
        view.add_after_call.side_effect = ValueError
        with pytest.raises(JHTTPBadRequest):
            wrappers.set_public_limits(view)

    @patch('nefertari.wrappers.set_total')
    @patch('nefertari.wrappers.set_public_count')
    def test_set_public_limits_count(self, mock_count, mock_set):
        request = Mock()
        request.registry.settings = {'public_max_limit': 123}
        view = Mock(
            request=request,
            _query_params={
                '_limit': 100, '_page': 1, '_start': 90,
                '_count': ''})
        wrappers.set_public_limits(view)
        mock_count.assert_called_once_with(request, public_max=123)
        view.add_after_call.assert_called_with(
            'index', mock_count(), pos=0)
        assert view.add_after_call.call_count == 2

    def test_set_public_count(self):
        wrapper = wrappers.set_public_count(None, public_max=10)
        assert wrapper(result=1) == 1
        assert wrapper(result=5) == 5
        assert wrapper(result=15) == 10


class TestApplyPrivacy(object):
    model_test_data = TestWrappers.model_test_data

    def test_no_data(self):
        assert wrappers.apply_privacy(None)(result={}) == {}

    @patch('nefertari.wrappers.engine')
    def test_item_non_auth(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=['id'],
            _hidden_fields=[])
        mock_eng.get_document_cls.return_value = document_cls
        request = Mock(user=None)
        filtered = wrappers.apply_privacy(request)(result=self.model_test_data)
        assert list(sorted(filtered.keys())) == [
            '_pk', '_self', '_type', 'desc', 'name']

    @patch('nefertari.wrappers.engine')
    def test_item_no_request(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=['id'],
            _hidden_fields=[])
        mock_eng.get_document_cls.return_value = document_cls
        filtered = wrappers.apply_privacy(None)(result=self.model_test_data)
        assert list(sorted(filtered.keys())) == [
            '_pk', '_self', '_type', 'desc', 'id', 'name', 'other_field']

    @patch('nefertari.wrappers.engine')
    def test_item_auth(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=['id'],
            _hidden_fields=[])
        mock_eng.get_document_cls.return_value = document_cls
        request = Mock(user=Mock())
        filtered = wrappers.apply_privacy(request)(
            result=self.model_test_data, is_admin=False)
        assert list(sorted(filtered.keys())) == [
            '_pk', '_self', '_type', 'id']

    @patch('nefertari.wrappers.engine')
    def test_item_auth_calculated(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=['id'],
            _hidden_fields=[])
        mock_eng.get_document_cls.return_value = document_cls

        class User(object):
            @classmethod
            def is_admin(self, obj):
                return False

        request = Mock(user=User())
        filtered = wrappers.apply_privacy(request)(result=self.model_test_data)
        assert list(sorted(filtered.keys())) == [
            '_pk', '_self', '_type', 'id']

    @patch('nefertari.wrappers.engine')
    def test_item_admin(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=['id'],
            _hidden_fields=[])
        mock_eng.get_document_cls.return_value = document_cls
        request = Mock(user=Mock())
        filtered = wrappers.apply_privacy(request)(
            result=self.model_test_data, is_admin=True)
        assert list(sorted(filtered.keys())) == [
            '_pk', '_self', '_type', 'desc', 'id', 'name', 'other_field']
        filtered['_type'] == 'foo'
        filtered['desc'] == 'User 1 data'
        filtered['id'] == 1
        filtered['name'] == 'User1'
        filtered['other_field'] == 123
        filtered['_self'] == 'http://example.com/1'
        mock_eng.get_document_cls.assert_called_once_with('foo')

    @patch('nefertari.wrappers.engine')
    def test_no_type(self, mock_eng):
        data = self.model_test_data.copy()
        data.pop('_type')
        request = Mock(user=Mock())
        filtered = wrappers.apply_privacy(request)(
            result=data, is_admin=True)
        assert list(sorted(filtered.keys())) == [
            '_pk', '_self', 'desc', 'id', 'name', 'other_field']
        filtered['desc'] == 'User 1 data'
        filtered['id'] == 1
        filtered['name'] == 'User1'
        filtered['other_field'] == 123
        filtered['_self'] == 'http://example.com/1'
        assert not mock_eng.get_document_cls.called

    @patch('nefertari.wrappers.engine')
    def test_not_dict(self, mock_eng):
        request = Mock(user=Mock())
        filtered = wrappers.apply_privacy(request)(
            result='foo', is_admin=True)
        assert filtered == 'foo'

    @patch('nefertari.wrappers.engine')
    def test_nested_data_not_dict(self, mock_eng):
        request = Mock(user=Mock())
        assert wrappers.apply_privacy(request)(
            result={'data': 'foo'}, is_admin=True) == {'data': 'foo'}
        assert wrappers.apply_privacy(request)(
            result={'data': 1}, is_admin=True) == {'data': 1}

    @patch('nefertari.wrappers.engine')
    def test_item_admin_calculated(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=['id'],
            _hidden_fields=[])
        mock_eng.get_document_cls.return_value = document_cls

        class User(object):
            @classmethod
            def is_admin(self, obj):
                return True

        request = Mock(user=User())
        filtered = wrappers.apply_privacy(request)(result=self.model_test_data)
        assert list(sorted(filtered.keys())) == [
            '_pk', '_self', '_type', 'desc', 'id', 'name', 'other_field']
        filtered['_type'] == 'foo'
        filtered['desc'] == 'User 1 data'
        filtered['id'] == 1
        filtered['name'] == 'User1'
        filtered['other_field'] == 123
        filtered['_self'] == 'http://example.com/1'
        mock_eng.get_document_cls.assert_called_once_with('foo')

    @patch('nefertari.wrappers.engine')
    def test_item_no_document_cls(self, mock_eng):
        mock_eng.get_document_cls.side_effect = ValueError
        request = Mock(user=Mock())
        filtered = wrappers.apply_privacy(request)(
            result=self.model_test_data, is_admin=True)
        assert list(sorted(filtered.keys())) == [
            '_pk', '_self', '_type', 'desc', 'id', 'name', 'other_field']

    @patch('nefertari.wrappers.engine')
    def test_item_no_fields(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=[],
            _hidden_fields=[])
        mock_eng.get_document_cls.return_value = document_cls
        request = Mock(user=Mock())
        filtered = wrappers.apply_privacy(request)(
            result=self.model_test_data, is_admin=False)
        assert list(sorted(filtered.keys())) == ['_pk', '_self', '_type']

    @patch('nefertari.wrappers.engine')
    def test_collection(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=['id'],
            _hidden_fields=[])
        mock_eng.get_document_cls.return_value = document_cls
        request = Mock(user=Mock())
        result = {
            'total': 1,
            'count': 1,
            'data': [self.model_test_data]
        }
        filtered = wrappers.apply_privacy(request)(
            result=result, is_admin=False)
        assert list(sorted(filtered.keys())) == ['count', 'data', 'total']
        assert len(filtered['data']) == 1
        data = filtered['data'][0]
        assert list(sorted(data.keys())) == ['_pk', '_self', '_type', 'id']

    @patch('nefertari.wrappers.engine')
    def test_apply_nested_privacy_dict(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=['id'],
            _hidden_fields=[])
        mock_eng.get_document_cls.return_value = document_cls
        request = Mock(user=Mock())
        data = {'owner': self.model_test_data}
        wrapper = wrappers.apply_privacy(request)
        wrapper.is_admin = False
        wrapper.drop_hidden = False
        filtered = wrapper._apply_nested_privacy(data)
        assert list(filtered.keys()) == ['owner']
        owner = filtered['owner']
        assert sorted(owner.keys()) == [
            '_pk', '_self', '_type', 'id']

    @patch('nefertari.wrappers.engine')
    def test_apply_nested_privacy_list(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=['id'],
            _hidden_fields=[])
        mock_eng.get_document_cls.return_value = document_cls
        request = Mock(user=Mock())
        data = {'owner': [self.model_test_data]}
        wrapper = wrappers.apply_privacy(request)
        wrapper.is_admin = False
        wrapper.drop_hidden = False
        filtered = wrapper._apply_nested_privacy(data)
        assert list(filtered.keys()) == ['owner']
        owner = filtered['owner'][0]
        assert sorted(owner.keys()) == [
            '_pk', '_self', '_type', 'id']

    @patch('nefertari.wrappers.engine')
    def test_simple_call_with_nested(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=['id', 'creator'],
            _hidden_fields=[])
        mock_eng.get_document_cls.return_value = document_cls
        request = Mock(user=Mock())
        data = {
            'id': 1,
            '_type': 'foo1',
            'username': 'admin',
            'creator': {
                'id': 2,
                '_type': 'foo2',
                'creator': 'foo',
                'address': 'adsasd',
            }
        }
        filtered = wrappers.apply_privacy(request)(
            result=data, is_admin=False)
        assert filtered == {
            '_type': 'foo1',
            'id': 1,
            'creator': {
                '_type': 'foo2',
                'creator': 'foo',
                'id': 2
            }

        }

    @patch('nefertari.wrappers.engine')
    def test_hidden_fields_drop(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=['id', 'name'],
            _hidden_fields=['name'])
        mock_eng.get_document_cls.return_value = document_cls
        request = Mock(user=Mock())
        filtered = wrappers.apply_privacy(request)(
            result=self.model_test_data, is_admin=False,
            drop_hidden=True)
        assert list(sorted(filtered.keys())) == [
            '_pk', '_self', '_type', 'id']

    @patch('nefertari.wrappers.engine')
    def test_hidden_fields_not_drop(self, mock_eng):
        document_cls = Mock(
            _public_fields=['name', 'desc'],
            _auth_fields=['id'],
            _hidden_fields=['name'])
        mock_eng.get_document_cls.return_value = document_cls
        request = Mock(user=Mock())
        filtered = wrappers.apply_privacy(request)(
            result=self.model_test_data, is_admin=False,
            drop_hidden=False)
        assert list(sorted(filtered.keys())) == [
            '_pk', '_self', '_type', 'id', 'name']
