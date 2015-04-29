#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest

from mock import Mock, patch
from pyramid.testing import DummyRequest

from nefertari import wrappers


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
