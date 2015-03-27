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
