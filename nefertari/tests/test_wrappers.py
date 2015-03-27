#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest
import mock
from nefertari import wrappers
from nefertari.view import BaseView
from nefertari.utils import dictset


class WrappersTest(unittest.TestCase):

    def test_validator_decorator(self):
        params = dictset(a=10, b='bbb', c=20, mixed=lambda: {})

        req = mock.MagicMock(params=params)
        res = mock.MagicMock(actions=['create', 'update', 'index'])

        class MyView(BaseView):

            __validation_schema__ = dict(
                a=dict(type=int, required=True),
                b=dict(type=str, required=False)
            )

            def __init__(self):
                BaseView.__init__(self, res, req)

            @wrappers.validator(c=dict(type=int, required=True),
                                a=dict(type=float, required=False))
            def create(self):
                pass

            @wrappers.validator()
            def update(self):
                pass

            @wrappers.validator(a=dict(type=int, required=False))
            def index(self):
                []

            def convert_ids2objects(self, *args, **kwargs):
                pass

        view = MyView()
        self.assertEqual([wrappers.validate_types(),
                         wrappers.validate_required()],
                         view.create._before_calls)
        self.assertIn('c', view.create._before_calls[0].kwargs)

        self.assertEqual(dict(type=float, required=False),
                         view.create._before_calls[0].kwargs['a'])

    def test_validate_types(self):
        import datetime as dt

        request = mock.MagicMock()
        wrappers.validate_types()(request=request)

        schema = dict(a=dict(type=int), b=dict(type=str),
                      c=dict(type=dt.datetime), d=dict(type=dt.date),
                      e=dict(type=None), f=dict(type='BadType'))

        request.params = dict(a=1, b=2)
        wrappers.validate_types(**schema)(request=request)

        request.params = dict(c='2000-01-01T01:01:01')
        wrappers.validate_types(**schema)(request=request)

        request.params = dict(d='2000-01-01')
        wrappers.validate_types(**schema)(request=request)

        request.params = dict(c='bad_date')
        with self.assertRaises(wrappers.ValidationError):
            wrappers.validate_types(**schema)(request=request)

        request.params = dict(d='bad_date')
        with self.assertRaises(wrappers.ValidationError):
            wrappers.validate_types(**schema)(request=request)

        request.params = dict(e='unknown_type')
        with mock.patch('nefertari.wrappers.log') as log:
            wrappers.validate_types(**schema)(request=request)
            self.assertTrue(log.debug.called)

        request.params = dict(f='bad_type')
        with self.assertRaises(wrappers.ValidationError):
            wrappers.validate_types(**schema)(request=request)

    def test_validate_required(self):
        request = mock.MagicMock()
        wrappers.validate_types()(request=request)

        schema = dict(a=dict(type=int, required=True), b=dict(type=str,
                      required=False), c=dict(type=int))

        request.params = dict(a=1, b=2, c=3)
        wrappers.validate_required(**schema)(request=request)

        request.params = dict(a=1, b=2)
        wrappers.validate_required(**schema)(request=request)

        request.params = dict(a=1, c=3)
        wrappers.validate_required(**schema)(request=request)

        request.params = dict(b=2, c=3)
        with self.assertRaises(wrappers.ValidationError):
            wrappers.validate_required(**schema)(request=request)

    def test_obj2dict(self):
        result = mock.MagicMock()
        result.to_dict.return_value = dict(a=1)

        res = wrappers.obj2dict(request=None)(result=result)
        self.assertEqual(dict(a=1), res)

        result.to_dict.return_value = [dict(a=1), dict(b=2)]
        self.assertEqual([dict(a=1), dict(b=2)],
                         wrappers.obj2dict(request=None)(result=result))

        special = mock.MagicMock()
        special.to_dict.return_value = {'special': 'dict'}
        result = ['a', 'b', special]
        self.assertEqual(['a', 'b', {'special': 'dict'}],
                         wrappers.obj2dict(request=None)(result=result))

        self.assertEqual([], wrappers.obj2dict(request=None)(result=[]))
