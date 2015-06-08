from datetime import datetime

import pytest

from nefertari.utils.dictset import dictset


class TestDictset(object):
    def test_copy(self):
        dset1 = dictset({'foo': 'bar'})
        dset2 = dset1.copy()
        assert dset1 is not dset2
        assert dset1 == dset2

    def test_subset_no_keys(self):
        dset1 = dictset({'foo': 'bar', 'fruit': 'apple'})
        dset2 = dset1.subset([])
        assert dset1 is not dset2
        assert dset1 != dset2

    def test_subset(self):
        dset1 = dictset({'foo': 'bar', 'fruit': 'apple'})
        dset2 = dset1.subset(['foo', 'nonexisting'])
        assert dict(dset2) == {'foo': 'bar'}

    def test_subset_exclude(self):
        dset1 = dictset({'foo': 'bar', 'fruit': 'apple'})
        dset2 = dset1.subset(['-fruit', '-nonexisting'])
        assert dict(dset2) == {'foo': 'bar'}

    def test_remove(self):
        dset1 = dictset({'foo': 'bar', 'fruit': 'apple'})
        dset2 = dset1.remove(['fruit'])
        assert dict(dset2) == {'foo': 'bar'}

    def test_getattr(self):
        dset1 = dictset({'foo': 'bar', 'fruit': 'apple'})
        assert dset1.foo == 'bar'
        assert dset1.fruit == 'apple'

    def test_setattr(self):
        dset1 = dictset()
        dset1.boo = 1
        assert dict(dset1) == {'boo': 1}

    def test_asbool(self):
        dset1 = dictset({
            'foo': 'true', 'fruit': 'false',
            'baz': True, 'zoo': False})
        assert dset1.asbool('foo')
        assert dset1.asbool('baz')
        assert isinstance(dset1.asbool('foo'), bool)
        assert isinstance(dset1.asbool('baz'), bool)
        assert not dset1.asbool('fruit')
        assert not dset1.asbool('zoo')

    def test_asbool_set(self):
        dset1 = dictset({'foo': 'true'})
        assert dset1.asbool('foo', _set=True)
        assert dset1.foo
        assert dset1.foo != 'true'

    def test_asbool_pop(self):
        dset1 = dictset({'foo': 'true'})
        assert dset1.asbool('foo', pop=True)
        assert 'foo' not in dset1

    def test_asbool_default(self):
        dset1 = dictset({'foo': 'true'})
        assert dset1.asbool('foo1', default=True)
        assert 'foo1' not in dset1

    def test_aslist(self):
        dset1 = dictset({'foo': '1,2, 3'})
        assert dset1.aslist('foo') == ['1', '2', '3']

    def test_aslist_set(self):
        dset1 = dictset({'foo': '1,2,3'})
        assert dset1.aslist('foo', _set=True) == ['1', '2', '3']
        assert dset1.foo == ['1', '2', '3']

    def test_aslist_default(self):
        dset1 = dictset({'foo': '1,2,3'})
        assert dset1.aslist('foo1', default=['1']) == ['1']
        assert 'foo1' not in dset1

    def test_asint(self):
        assert dictset({'foo': '1'}).asint('foo') == 1

    def test_asint_set(self):
        dset = dictset({'foo': '1'})
        assert dset.asint('foo', _set=True) == 1
        assert dset.foo == 1

    def test_asint_default(self):
        dset = dictset({'foo': '1'})
        assert dset.asint('foo1', default=2) == 2
        assert 'foo1' not in dset

    def test_asfloat(self):
        assert dictset({'foo': '1.0'}).asfloat('foo') == 1.0

    def test_asfloat_set(self):
        dset = dictset({'foo': '1.0'})
        assert dset.asfloat('foo', _set=True) == 1.0
        assert dset.foo == 1.0

    def test_asfloat_default(self):
        dset = dictset({'foo': '1.0'})
        assert dset.asfloat('foo1', default=2.0) == 2.0
        assert 'foo1' not in dset

    def test_asdict(self):
        dset = dictset({'foo': "a:2,b:blabla,c:True,a:'d',a:1"})
        assert dset.asdict('foo') == {
            'a': ['2', "'d'", '1'], 'b': 'blabla', 'c': 'True'}

    def test_asdict_type(self):
        dset = dictset({'foo': "a:2,a:1"})
        assert dset.asdict('foo', _type=lambda x: int(x)) == {'a': [2, 1]}

    def test_asdict_set(self):
        dset = dictset({'foo': "a:2,b:blabla,c:True,a:'d',a:1"})
        assert dset.asdict('foo', _set=True) == {
            'a': ['2', "'d'", '1'], 'b': 'blabla', 'c': 'True'}
        assert dset.foo == {
            'a': ['2', "'d'", '1'], 'b': 'blabla', 'c': 'True'}

    def test_asdict_wrong_key(self):
        dset = dictset({'foo': "a:2,b:blabla,c:True,a:'d',a:1"})
        assert dset.asdict('boo') == {}

    def test_mget(self):
        dset = dictset({'foo.key1': '1', 'foo.key2': '2', 'boo': '3'})
        dset2 = dset.mget('foo')
        assert dset2 == {'key1': '1', 'key2': '2'}

    def test_mget_defaults(self):
        dset = dictset({'foo.key1': '1', 'foo.key2': '2', 'boo': '3'})
        dset2 = dset.mget('foo', defaults={'q': 1})
        assert dset2 == {'key1': '1', 'key2': '2', 'q': 1}

    def test_update(self):
        dset = dictset({'boo': '3'})
        dset2 = dset.update(foo=1)
        assert dset.foo == 1
        assert dset is dset2

    def test_process_list_param_string(self):
        dset = dictset({'boo': '1,2'})
        assert dset.process_list_param('boo') == ['1', '2']
        assert dset.boo == ['1', '2']

    def test_process_list_param_setdefault(self):
        dset = dictset({'boo': '1,2'})
        assert dset.process_list_param('foo', setdefault=[1]) == [1]
        assert dset.foo == [1]

    def test_process_list_param_default(self):
        dset = dictset({'boo': '1,2'})
        assert dset.process_list_param('foo', default=[1]) == [1]
        assert 'foo' not in dset

    def test_process_list_param_pop(self):
        dset = dictset({'boo': '1,2'})
        assert dset.process_list_param('boo', pop=True) == ['1', '2']
        assert 'boo' not in dset

    def test_process_list_param_pop_default(self):
        dset = dictset({'boo': '1,2'})
        assert dset.process_list_param('foo', default=[1], pop=True) == [1]
        assert 'foo' not in dset

    def test_process_list_param_type(self):
        dset = dictset({'boo': '1,2'})
        assert dset.process_list_param('boo', _type=lambda x: int(x)) == [1, 2]

    def test_process_bool_param(self):
        dset = dictset({'boo': 'true', 'foo': 'false'})
        assert dset.process_bool_param('boo')
        assert not dset.process_bool_param('foo')
        assert dset.boo
        assert not dset.foo
        assert isinstance(dset.boo, bool)
        assert isinstance(dset.foo, bool)

    def test_process_bool_param_default(self):
        dset = dictset({'boo': 'true'})
        assert dset.process_bool_param('foo', default=True)
        assert dset.foo
        assert isinstance(dset.foo, bool)

    def test_pop_bool_param(self):
        dset = dictset({'boo': 'true'})
        param = dset.pop_bool_param('boo')
        assert param
        assert isinstance(param, bool)
        assert 'boo' not in dset

    def test_pop_bool_param_default(self):
        dset = dictset({'boo': 'true'})
        param = dset.pop_bool_param('foo', default=True)
        assert param
        assert isinstance(param, bool)
        assert 'foo' not in dset

    def test_process_datetime_param(self):
        dset = dictset({'boo': '2014-01-02T03:04:05Z'})
        dtime = dset.process_datetime_param('boo')
        assert dtime is dset.boo
        assert dtime == dset.boo
        assert isinstance(dtime, datetime)
        assert dtime.year == 2014
        assert dtime.month == 1
        assert dtime.day == 2
        assert dtime.hour == 3
        assert dtime.minute == 4
        assert dtime.second == 5

    def test_process_datetime_param_wrong_format(self):
        dset = dictset({'boo': '2014-01-'})
        with pytest.raises(ValueError) as ex:
            dset.process_datetime_param('boo')
        assert 'Bad format' in str(ex.value)

    def test_process_float_param(self):
        dset = dictset({'boo': '1.5'})
        assert dset.process_float_param('boo') == 1.5
        assert dset.boo == 1.5

    def test_process_float_param_value_err(self):
        dset = dictset({'boo': 'a'})
        with pytest.raises(ValueError) as ex:
            dset.process_float_param('boo')
        assert 'boo must be a decimal' == str(ex.value)

    def test_process_float_param_default(self):
        dset = dictset({'boo': '1.5'})
        assert dset.process_float_param('foo', default=2.5) == 2.5
        assert dset.foo == 2.5

    def test_process_int_param(self):
        dset = dictset({'boo': '1'})
        assert dset.process_int_param('boo') == 1
        assert dset.boo == 1

    def test_process_int_param_value_err(self):
        dset = dictset({'boo': 'a'})
        with pytest.raises(ValueError) as ex:
            dset.process_int_param('boo')
        assert 'boo must be an integer' == str(ex.value)

    def test_process_int_param_default(self):
        dset = dictset({'boo': '1'})
        assert dset.process_int_param('foo', default=2) == 2
        assert dset.foo == 2

    def test_process_dict_param(self):
        dset = dictset({'boo': 'a:1'})
        assert dset.process_dict_param('boo') == {'a': '1'}
        assert dset.boo == {'a': '1'}

    def test_process_dict_param_type(self):
        dset = dictset({'boo': 'a:1'})
        assert dset.process_dict_param('boo', _type=lambda x: int(x)) == {
            'a': 1}
        assert dset.boo == {'a': 1}

    def test_process_dict_param_pop(self):
        dset = dictset({'boo': 'a:1'})
        assert dset.process_dict_param('boo', pop=True) == {'a': '1'}
        assert 'boo' not in dset

    def test_pop_by_values(self):
        dset = dictset({'boo': '1', 'foo': '2'})
        dset.pop_by_values('3')
        assert dict(dset) == {'boo': '1', 'foo': '2'}
        dset.pop_by_values('1')
        assert dict(dset) == {'foo': '2'}
        dset.pop_by_values('2')
        assert dict(dset) == {}
