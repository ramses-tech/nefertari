#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest

from mock import Mock
from pyramid.testing import DummyRequest

from nefertari import wrappers


class WrappersTest(unittest.TestCase):

    def test_obj2dict(self):
        result = Mock()
        result.to_dict.return_value = dict(a=1)

        res = wrappers.obj2dict(request=None)(result=result)
        self.assertEqual(dict(a=1), res)

        result.to_dict.return_value = [dict(a=1), dict(b=2)]
        self.assertEqual([dict(a=1), dict(b=2)],
                         wrappers.obj2dict(request=None)(result=result))

        special = Mock()
        special.to_dict.return_value = {'special': 'dict'}
        result = ['a', 'b', special]
        self.assertEqual(['a', 'b', {'special': 'dict'}],
                         wrappers.obj2dict(request=None)(result=result))

        self.assertEqual([], wrappers.obj2dict(request=None)(result=[]))

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
