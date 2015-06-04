import pytest
from mock import patch, call

from nefertari.utils import utils


class TestUtils(object):

    @patch('nefertari.utils.utils.json')
    def test_json_dumps(self, mock_json):
        from nefertari.renderers import _JSONEncoder
        utils.json_dumps('foo')
        mock_json.dumps.assert_called_once_with('foo', cls=_JSONEncoder)

    @patch('nefertari.utils.utils.json')
    def test_json_dumps_encoder(self, mock_json):
        utils.json_dumps('foo', 'enc')
        mock_json.dumps.assert_called_once_with('foo', cls='enc')

    def test_split_strip(self):
        assert utils.split_strip('1, 2,') == ['1', '2']
        assert utils.split_strip('1, 2') == ['1', '2']
        assert utils.split_strip('1;2;', on=';') == ['1', '2']

    def test_process_limit_start_and_page(self):
        with pytest.raises(ValueError) as ex:
            utils.process_limit(1, 2, 3)
        assert 'at the same time' in str(ex.value)

    def test_process_limit_start(self):
        start, limit = utils.process_limit(start=1, page=None, limit=5)
        assert start == 1
        assert limit == 5

    def test_process_limit_page(self):
        start, limit = utils.process_limit(start=None, page=2, limit=5)
        assert start == 10
        assert limit == 5

    def test_process_limit_no_start_page(self):
        start, limit = utils.process_limit(start=None, page=None, limit=5)
        assert start == 0
        assert limit == 5

    def test_process_limit_lower_than_zero(self):
        with pytest.raises(ValueError) as ex:
            utils.process_limit(1, None, -3)
        assert 'can not be < 0' in str(ex.value)
        with pytest.raises(ValueError) as ex:
            utils.process_limit(-1, None, 3)
        assert 'can not be < 0' in str(ex.value)

    def test_extend_list_string(self):
        assert utils.extend_list('foo, bar,') == ['foo', 'bar']

    def test_extend_list_sequence_string(self):
        assert utils.extend_list(['foo, bar,']) == ['foo', 'bar']

    def test_extend_list_sequence_elements(self):
        assert utils.extend_list(['foo', 'bar', '1,2']) == [
            'foo', 'bar', '1', '2']

    def test_process_fields_string(self):
        only, exclude = utils.process_fields('a,b,-c')
        assert only == ['a', 'b']
        assert exclude == ['c']

    def test_process_fields_empty_field(self):
        only, exclude = utils.process_fields(['a', 'b', '-c', ''])
        assert only == ['a', 'b']
        assert exclude == ['c']

    def test_snake2camel(self):
        assert utils.snake2camel('foo_bar') == 'FooBar'
        assert utils.snake2camel('foobar') == 'Foobar'

    @patch('nefertari.utils.utils.Configurator')
    def test_maybe_dotted(self, mock_conf):
        result = utils.maybe_dotted('foo.bar')
        mock_conf.assert_called_once_with()
        mock_conf().maybe_dotted.assert_called_once_with('foo.bar')
        assert result == mock_conf().maybe_dotted()

    @patch('nefertari.utils.utils.Configurator')
    def test_maybe_dotted_err_throw(self, mock_conf):
        mock_conf.side_effect = ImportError
        with pytest.raises(ImportError):
            utils.maybe_dotted('foo.bar', throw=True)

    @patch('nefertari.utils.utils.Configurator')
    def test_maybe_dotted_err_no_throw(self, mock_conf):
        mock_conf.side_effect = ImportError
        assert utils.maybe_dotted('foo.bar', throw=False) is None

    @patch('nefertari.utils.utils.os')
    def test_chdir(self, mock_os):
        with utils.chdir('/tmp'):
            pass
        mock_os.getcwd.assert_called_once_with()
        mock_os.chdir.assert_has_calls([
            call('/tmp'), call(mock_os.getcwd())
        ])

    def test_isnumeric(self):
        from decimal import Decimal
        assert not utils.isnumeric('asd')
        assert not utils.isnumeric(dict())
        assert not utils.isnumeric([])
        assert not utils.isnumeric(())
        assert utils.isnumeric(1)
        assert utils.isnumeric(2.0)
        assert utils.isnumeric(Decimal(1))

    def test_issequence(self):
        assert utils.issequence(dict())
        assert utils.issequence([])
        assert utils.issequence(())
        assert not utils.issequence('asd')
        assert not utils.issequence(1)
        assert not utils.issequence(2.0)

    def test_merge_dicts(self):
        dict1 = {'a': {'b': {'c': 1}}}
        dict2 = {'a': {'d': 2}, 'q': 3}
        merged = utils.merge_dicts(dict1, dict2)
        assert merged == {
            'a': {
                'b': {'c': 1},
                'd': 2,
            },
            'q': 3
        }

    def test_str2dict(self):
        assert utils.str2dict('foo.bar') == {'foo': {'bar': {}}}

    def test_str2dict_value(self):
        assert utils.str2dict('foo.bar', value=2) == {'foo': {'bar': 2}}

    def test_str2dict_separator(self):
        assert utils.str2dict('foo:bar', value=2, separator=':') == {
            'foo': {'bar': 2}}
