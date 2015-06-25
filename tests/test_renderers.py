#!/usr/bin/python
# -*- coding: utf-8 -*-

from datetime import datetime, date
from decimal import Decimal
import json
import unittest

import mock

from nefertari import renderers


class TestRenderers(unittest.TestCase):

    def setUp(self):
        self.now = datetime.utcnow()
        self.today = date.today()

    def _get_dummy_result(self):
        obj = {
            'integer': 1,
            'string': "hello world",
            'unicode': u"yéyé",
            'list': [1, 2, 3, 4],
            'obj': {
                'wow': {
                    'yop': 'opla'
                }
            },
            'price': Decimal('102.3'),
            'datetime': self.now.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'date': self.today.strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        return obj

    def _get_dummy_expected(self):
        return {
            'integer': 1,
            'string': "hello world",
            'unicode': u"yéyé",
            'list': [1, 2, 3, 4],
            'obj': {
                'wow': {
                    'yop': 'opla'
                }
            },
            'price': str(Decimal('102.3')),
            'datetime': self.now.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'date': self.today.strftime('%Y-%m-%dT%H:%M:%SZ')
        }

    def test_JSONEncoder_datetime_decimal(self):
        res_obj = self._get_dummy_result()
        exp_obj = self._get_dummy_expected()

        res_dumps = json.dumps(res_obj, cls=renderers._JSONEncoder)
        exp_dumps = json.dumps(exp_obj)

        self.assertDictEqual(json.loads(exp_dumps), json.loads(res_dumps))

        enc = renderers._JSONEncoder()
        self.assertEqual(self.now.strftime('%Y-%m-%dT%H:%M:%SZ'),
                         enc.default(self.now))
        # self.assertRaises(TypeError, enc.default, {})

    def test_JsonRendererFactory(self):

        request = mock.MagicMock()
        request.response.default_content_type = 'text/html'
        request.response.content_type = 'text/html'
        request.url = 'http://'
        view = mock.Mock()
        view._json_encoder = None

        factory = renderers.JsonRendererFactory({
            'name': 'json',
            'package': None,
            'registry': None
        })

        result = json.loads(factory(
            self._get_dummy_result(),
            {'request': request, 'view': view}))
        self.assertDictContainsSubset(self._get_dummy_expected(), result)
        self.assertEqual('application/json', request.response.content_type)

    @mock.patch('nefertari.renderers.wrappers')
    def test_JsonRendererFactory_run_after_calls(self, mock_wrap):
        factory = renderers.JsonRendererFactory({
            'name': 'json',
            'package': None,
            'registry': None
        })
        request = mock.Mock(action='create')
        factory.run_after_calls(1, {'request': request})
        assert not mock_wrap.wrap_in_dict.called

        request = mock.Mock(action='show')
        factory.run_after_calls(1, {'request': request})
        mock_wrap.wrap_in_dict.assert_called_once_with(request)
        mock_wrap.wrap_in_dict().assert_called_once_with(result=1)

    def test_NefertariJsonRendererFactory_run_after_calls(self):
        factory = renderers.NefertariJsonRendererFactory(None)
        filters = {
            'super_action': [lambda request, result: result + ' processed'],
        }
        request = mock.Mock(action='super_action', filters=filters)
        processed = factory.run_after_calls('foo', {'request': request})
        assert processed == 'foo processed'

    def test_NefertariJsonRendererFactory_run_after_calls_no_filters(self):
        factory = renderers.NefertariJsonRendererFactory(None)
        request = mock.Mock(action='action', filters={})
        processed = factory.run_after_calls('foo', {'request': request})
        assert processed == 'foo'

    def test_NefertariJsonRendererFactory_run_after_calls_unknown_action(self):
        factory = renderers.NefertariJsonRendererFactory(None)
        filter = {
            'super_action': [lambda request, result: result + ' processed'],
        }
        request = mock.Mock(action='simple_action', filters=filter)
        request = mock.Mock(action='action', filters={})
        processed = factory.run_after_calls('foo', {'request': request})
        assert processed == 'foo'


class TestDefaultResponseRendererMixin(object):

    def _system_mocks(self):
        return {
            'view': mock.Mock(
                _json_encoder=None,
                Model=mock.Mock(__name__='Foo'),
            ),
            'request': mock.Mock(action='create')
        }

    def test_get_common_kwargs(self):
        system = self._system_mocks()
        system['view']._json_encoder = 1
        mixin = renderers.DefaultResponseRendererMixin()
        data = mixin._get_common_kwargs(system)
        assert sorted(data.keys()) == ['encoder', 'request']
        assert data['request'].action == 'create'
        assert data['encoder'] == 1

    def test_get_common_kwargs_default_encoder(self):
        system = self._system_mocks()
        mixin = renderers.DefaultResponseRendererMixin()
        data = mixin._get_common_kwargs(system)
        assert sorted(data.keys()) == ['encoder', 'request']
        assert data['request'].action == 'create'
        assert data['encoder'] == renderers._JSONEncoder

    @mock.patch('nefertari.renderers.JHTTPCreated')
    def test_render_create(self, mock_resp):
        system = self._system_mocks()
        system['view']._resource.id_name = 'story_id'
        system['view']._resource.uid = 'user:stories'
        value = mock.Mock(id=1)
        value.pk_field.return_value = 'id'
        value.to_dict.return_value = {'q': 'd'}
        mixin = renderers.DefaultResponseRendererMixin()
        mixin.render_create(value, system, {'a': 'b'})
        system['request'].route_url.assert_called_once_with(
            'user:stories', story_id=1)
        mock_resp.assert_called_once_with(
            a='b', resource={'q': 'd'},
            location=system['request'].route_url())

    @mock.patch('nefertari.renderers.JHTTPOk')
    def test_render_update(self, mock_resp):
        system = self._system_mocks()
        system['view']._resource.id_name = 'story_id'
        system['view']._resource.uid = 'user:stories'
        value = mock.Mock(id=1)
        value.pk_field.return_value = 'id'
        mixin = renderers.DefaultResponseRendererMixin()
        mixin.render_update(value, system, {'a': 'b'})
        system['request'].route_url.assert_called_once_with(
            'user:stories', story_id=1)
        mock_resp.assert_called_once_with(
            "Updated", a='b', location=system['request'].route_url())

    def test_render_replace(self):
        mixin = renderers.DefaultResponseRendererMixin()
        mixin.render_update = mock.Mock()
        mixin.render_replace(1, 2)
        mixin.render_update.assert_called_once_with(1, 2)

    @mock.patch('nefertari.renderers.JHTTPOk')
    def test_render_delete(self, mock_resp):
        mixin = renderers.DefaultResponseRendererMixin()
        mixin.render_delete(None, None, {'a': 'b'})
        mock_resp.assert_called_once_with('Deleted', a='b')

    @mock.patch('nefertari.renderers.JHTTPOk')
    def test_render_delete_many_dict(self, mock_resp):
        mixin = renderers.DefaultResponseRendererMixin()
        mixin.render_delete_many({'foo': 1}, None, {'a': 'b'})
        mock_resp.assert_called_once_with(extra={'foo': 1})

    @mock.patch('nefertari.renderers.JHTTPOk')
    def test_render_delete_many_int(self, mock_resp):
        system = self._system_mocks()
        mixin = renderers.DefaultResponseRendererMixin()
        mixin.render_delete_many(13, system, {'a': 'b'})
        mock_resp.assert_called_once_with(
            'Deleted 13 Foo(s) objects', a='b')

    @mock.patch('nefertari.renderers.JHTTPOk')
    def test_render_update_many(self, mock_resp):
        system = self._system_mocks()
        mixin = renderers.DefaultResponseRendererMixin()
        mixin.render_update_many(13, system, {'a': 'b'})
        mock_resp.assert_called_once_with(
            'Updated 13 Foo(s) objects', a='b')

    def test_render_response_no_request(self):
        system = self._system_mocks()
        system.pop('request')
        mixin = renderers.NefertariJsonRendererFactory(None)
        resp = mixin._render_response({'foo': 'bar'}, system)
        assert resp == '{"foo": "bar"}'

    def test_render_response_no_method(self):
        system = self._system_mocks()
        system['request'].action = 'index'
        mixin = renderers.NefertariJsonRendererFactory(None)
        resp = mixin._render_response({'foo': 'bar'}, system)
        assert resp == '{"foo": "bar"}'

    def test_render_response(self):
        system = self._system_mocks()
        system['request'].action = 'delete'
        mixin = renderers.NefertariJsonRendererFactory(None)
        mixin._render_response({'foo': 'bar'}, system)
        resp = system['request'].response.body
        resp = json.loads(resp.decode('utf-8'))
        assert sorted(resp.keys()) == sorted([
            'request_url', 'timestamp', 'title', 'status_code', 'explanation',
            'message'])
        assert resp['message'] == 'Deleted'
        assert resp['status_code'] == 200
