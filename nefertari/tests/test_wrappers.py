#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest
import mock
from nefertari import wrappers


class WrappersTest(unittest.TestCase):

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
