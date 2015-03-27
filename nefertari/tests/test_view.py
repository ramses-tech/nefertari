#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import mock
from webtest import TestApp
from pyramid.config import Configurator

from nefertari.view import BaseView
from nefertari.json_httpexceptions import *
from nefertari.wrappers import wrap_me


class TestBaseView(unittest.TestCase):

    def test_BaseView(self, *a):

        class UsersView(BaseView):

            def __init__(self, context, request):
                BaseView.__init__(self, context, request)

            def show(self, id):
                return u'John Doe'

            def convert_ids2objects(self, *args, **kwargs):
                pass

        request = mock.MagicMock(content_type='')
        request.matched_route.pattern = '/users'
        view = UsersView(request.context, request)

        self.assertEqual(u'John Doe', view.show(1))

        self.assertRaises(JHTTPMethodNotAllowed, view.index)

        with self.assertRaises(AttributeError):
            view.frobnicate()

        # delete is an allowed action, but it raises since BaseView
        # does not implement it.
        with self.assertRaises(JHTTPMethodNotAllowed):
            view.delete()

    def test_ViewMapper(self):
        from nefertari.view import ViewMapper

        bc1 = mock.Mock()
        bc3 = mock.Mock()
        bc2 = mock.Mock()
        ac1 = mock.Mock(return_value=['thing'])

        class MyView:

            def __init__(self, ctx, req):
                self._before_calls = {'index': [bc1], 'show': [bc3]}
                self._after_calls = {}

            @wrap_me(before=bc2)
            def index(self):
                return ['thing']

        request = mock.MagicMock()
        resource = mock.MagicMock(actions=['index'])

        wrapper = ViewMapper(**{'attr': 'index'})(MyView)
        resp = wrapper(resource, request)

        bc1.assert_called_with(request=request)

        self.assertFalse(bc2.called)
        self.assertFalse(bc3.called)

    def test_defalt_wrappers_and_wrap_me(self):
        from nefertari import wrappers

        self.maxDiff = None

        def before_call(*a):
            return a[2]

        def after_call(*a):
            return a[2]

        class MyView(BaseView):

            @wrappers.wrap_me(before=before_call, after=after_call)
            def index(self):
                return [1, 2, 3]

            def convert_ids2objects(self, *args, **kwargs):
                pass

        request = mock.MagicMock(content_type='')
        resource = mock.MagicMock(actions=['index'])
        view = MyView(resource, request)

        self.assertEqual(len(view._after_calls['index']), 3)
        self.assertEqual(len(view._after_calls['show']), 2)
        self.assertEqual(len(view._after_calls['delete']), 1)
        self.assertEqual(len(view._after_calls['delete_many']), 1)
        self.assertEqual(len(view._after_calls['update_many']), 1)

        self.assertEqual(view.index._before_calls, [before_call])
        self.assertEqual(view.index._after_calls, [after_call])
