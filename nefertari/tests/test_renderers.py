#!/usr/bin/python
# -*- coding: utf-8 -*-

from datetime import datetime, date
from decimal import Decimal
import json
import unittest

import mock


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
        from nefertari.renderers import _JSONEncoder
        res_obj = self._get_dummy_result()
        exp_obj = self._get_dummy_expected()

        res_dumps = json.dumps(res_obj, cls=_JSONEncoder)
        exp_dumps = json.dumps(exp_obj)

        self.assertDictEqual(json.loads(exp_dumps), json.loads(res_dumps))

        enc = _JSONEncoder()
        self.assertEqual(self.now.strftime('%Y-%m-%dT%H:%M:%SZ'),
                         enc.default(self.now))
        # self.assertRaises(TypeError, enc.default, {})

    def test_JsonRendererFactory(self):
        from nefertari.renderers import JsonRendererFactory

        request = mock.MagicMock()
        request.response.default_content_type = 'text/html'
        request.response.content_type = 'text/html'
        request.url = 'http://'
        view = mock.Mock()
        view._json_encoder = None

        factory = JsonRendererFactory({
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
        from nefertari.renderers import JsonRendererFactory
        factory = JsonRendererFactory({
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
        from nefertari.renderers import NefertariJsonRendererFactory
        factory = NefertariJsonRendererFactory(None)
        filters = {
            'super_action': [lambda request, result: result + ' processed'],
        }
        request = mock.Mock(action='super_action', filters=filters)
        processed = factory.run_after_calls('foo', {'request': request})
        assert processed == 'foo processed'

    def test_NefertariJsonRendererFactory_run_after_calls_no_filters(self):
        from nefertari.renderers import NefertariJsonRendererFactory
        factory = NefertariJsonRendererFactory(None)
        request = mock.Mock(action='action', filters={})
        processed = factory.run_after_calls('foo', {'request': request})
        assert processed == 'foo'

    def test_NefertariJsonRendererFactory_run_after_calls_unknown_action(self):
        from nefertari.renderers import NefertariJsonRendererFactory
        factory = NefertariJsonRendererFactory(None)
        filter = {
            'super_action': [lambda request, result: result + ' processed'],
        }
        request = mock.Mock(action='simple_action', filters=filter)
        request = mock.Mock(action='action', filters={})
        processed = factory.run_after_calls('foo', {'request': request})
        assert processed == 'foo'
