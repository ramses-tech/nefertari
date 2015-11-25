import datetime
import decimal

from mock import Mock, patch, call

from nefertari.engine import common


class TestJSONEncoderMixin(object):
    def _encode(self, data):
        return common.JSONEncoderMixin().default(data)

    def test_encode_datetime(self):
        result = self._encode(datetime.datetime(1963, 11, 22))
        assert result == '1963-11-22T00:00:00Z'

    def test_encode_date(self):
        result = self._encode(datetime.date(1963, 11, 22))
        assert result == '1963-11-22T00:00:00Z'

    def test_encode_timedelta(self):
        result = self._encode(datetime.timedelta(seconds=120, hours=1))
        assert result == 3720

    def test_encode_decimal(self):
        result = self._encode(decimal.Decimal(1.23))
        assert result == 1.23
        assert isinstance(result, float)


class TestJSONEncoder(object):
    def _encode(self, data):
        return common.JSONEncoder().default(data)

    def test_encode_to_dict_obj(self):
        obj = Mock()
        obj.to_dict.return_value = {'foo': 1}
        assert self._encode(obj) == {'foo': 1}


class TestMultiEngineMeta(object):
    def _create_obj(self, bases=(dict,), attrs=None):
        return common.MultiEngineMeta('Foo', bases, attrs or {'foo': 1})

    @patch.object(common.MultiEngineMeta, '_generate_secondary_model')
    def test_init(self, mock_gen):
        self._create_obj()
        mock_gen.assert_called_once_with('Foo', {'foo': 1})

    @patch.object(common.MultiEngineMeta, '_needs_generation')
    def test_generate_secondary_model_doesnt_need_gen(self, mock_needs):
        mock_needs.return_value = False
        obj = self._create_obj()
        assert not hasattr(obj, '_secondary')
        mock_needs.assert_called_once_with()

    @patch.object(common.MultiEngineMeta, '_needs_generation')
    @patch.object(common.MultiEngineMeta, '_recreate_fields')
    @patch.object(common, 'engine')
    def test_generate_secondary_model(
            self, mock_eng, mock_fields, mock_needs):
        class Foo(object):
            pass

        mock_needs.return_value = True
        mock_fields.return_value = {'bar': 2}
        mock_eng.secondary.BaseDocument = Foo
        mock_eng.secondary.dict = dict
        obj = self._create_obj()
        assert obj._secondary.foo == 1
        assert obj._secondary.bar == 2
        assert obj._secondary.__bases__ == obj.__bases__
        assert obj._secondary._primary is obj
        mock_needs.assert_called_once_with()
        mock_fields.assert_called_once_with()

    @patch.object(common.MultiEngineMeta, '_generate_secondary_model')
    @patch.object(common, 'engine')
    def test_needs_generation_abstract(self, mock_eng, mock_gen):
        obj = self._create_obj()
        mock_eng.secondary = 1
        obj._is_abstract = Mock(return_value=True)
        assert not obj._needs_generation()

    @patch.object(common.MultiEngineMeta, '_generate_secondary_model')
    @patch.object(common, 'engine')
    def test_needs_generation_no_secondary_engine(self, mock_eng, mock_gen):
        obj = self._create_obj()
        obj._is_abstract = Mock(return_value=False)
        mock_eng.secondary = None
        assert not obj._needs_generation()

    @patch.object(common.MultiEngineMeta, '_generate_secondary_model')
    @patch.object(common, 'engine')
    def test_needs_generation_already_generated(self, mock_eng, mock_gen):
        mock_eng.secondary = 1
        obj = self._create_obj()
        obj._is_abstract = Mock(return_value=False)
        obj._primary = 1
        assert not obj._needs_generation()
        obj._primary = None
        obj._secondary = 1
        assert not obj._needs_generation()

    @patch.object(common.MultiEngineMeta, '_generate_secondary_model')
    @patch.object(common, 'engine')
    def test_needs_generation_not_generated(self, mock_eng, mock_gen):
        mock_eng.secondary = 1
        obj = self._create_obj()
        obj._is_abstract = Mock(return_value=False)
        assert obj._needs_generation()

    @patch.object(common.MultiEngineMeta, '_generate_secondary_model')
    @patch.object(common.MultiEngineMeta, '_get_secondary')
    def test_recreate_fields(self, mock_sec, mock_gen):
        obj = self._create_obj()
        creator = Mock()
        obj._get_fields_creators = Mock(return_value={'username': creator})
        obj.get_field_params = Mock(return_value={'min_length': 123})
        mock_sec.side_effect = lambda x: x
        fields = obj._recreate_fields()
        obj._get_fields_creators.assert_called_once_with()
        obj.get_field_params.assert_called_once_with('username')
        mock_sec.assert_has_calls([call(123), call(creator)])
        creator.assert_called_once_with(min_length=123)
        assert fields == {'username': creator()}

    @patch.object(common.MultiEngineMeta, '_generate_secondary_model')
    @patch.object(common.MultiEngineMeta, '_get_secondary')
    def test_recreate_bases(self, mock_sec, mock_gen):
        mock_sec.side_effect = lambda x: 1
        obj = self._create_obj()
        assert obj._recreate_bases() == [1]
        mock_sec.assert_called_once_with(dict)

    @patch.object(common.MultiEngineMeta, '_generate_secondary_model')
    def test_get_secondary_not_cls(self, mock_gen):
        obj = self._create_obj()
        assert obj._get_secondary(1) == 1
        assert obj._get_secondary('b') == 'b'

    @patch.object(common.MultiEngineMeta, '_generate_secondary_model')
    @patch.object(common, 'engine')
    def test_get_secondary_exists_in_secondary(self, mock_eng, mock_gen):
        class Foo(object):
            pass

        mock_eng.secondary = Mock(Foo=123)
        obj = self._create_obj()
        assert obj._get_secondary(Foo) == 123

    @patch.object(common.MultiEngineMeta, '_generate_secondary_model')
    @patch.object(common, 'engine')
    def test_get_secondary_doesnt_exist_in_secondary(
            self, mock_eng, mock_gen):
        class Foo(object):
            pass

        mock_eng.secondary = Mock(spec=[])
        obj = self._create_obj()
        assert obj._get_secondary(Foo) is Foo
