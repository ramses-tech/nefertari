#!/usr/bin/python
# -*- coding: utf-8 -*-
import pytest
from mock import Mock, MagicMock, patch, call, PropertyMock

from nefertari.view import (
    BaseView, error_view, key_error_view, value_error_view)
from nefertari.utils import dictset
from nefertari.json_httpexceptions import (
    JHTTPBadRequest, JHTTPNotFound, JHTTPMethodNotAllowed)
from nefertari.wrappers import wrap_me, ValidationError, ResourceNotFound
from nefertari.renderers import _JSONEncoder


class DummyBaseView(BaseView):
    _json_encoder = _JSONEncoder


class TestViewMapper(object):

    @patch('nefertari.view.trigger_events')
    def test_trigger_events_called(self, mock_manager):
        from nefertari.view import ViewMapper

        class MyView(object):
            Model = Mock

            def __init__(self, ctx, req):
                self._before_calls = {}
                self._after_calls = {}
                self._json_params = {}
                self.context = 'foo'

            def index(self):
                return ['thing']

        request = MagicMock(
            json={'username': 'admin'},
            body='{"username":"admin"}')
        resource = MagicMock(actions=['index'])

        wrapper = ViewMapper(**{'attr': 'index'})(MyView)
        wrapper(resource, request)
        assert mock_manager.called

    def test_viewmapper(self):
        from nefertari.view import ViewMapper

        bc1 = Mock()
        bc3 = Mock()
        bc2 = Mock()

        class MyView(object):
            Model = Mock
            _response = None

            def __init__(self, ctx, req):
                self._before_calls = {'index': [bc1], 'show': [bc3]}
                self._after_calls = {'show': [bc2]}
                self._json_params = {}
                self.context = 'foo'
                self.request = Mock(action='index')

            @wrap_me(before=bc2)
            def index(self):
                return ['thing']

        request = MagicMock()
        resource = MagicMock(actions=['index'])

        wrapper = ViewMapper(**{'attr': 'index'})(MyView)
        result = wrapper(resource, request)

        assert request.filters == {'show': [bc2]}
        assert request.action == 'index'
        assert result == ['thing']

        bc1.assert_called_with(request=request)
        assert not bc2.called
        assert not bc3.called

    def test_viewmapper_bad_request(self):
        from nefertari.view import ViewMapper

        bc1 = Mock(side_effect=ValidationError)

        class MyView(object):
            Model = Mock

            def __init__(self, ctx, req):
                self._before_calls = {'index': [bc1]}
                self._after_calls = {}

            def index(self):
                return ['thing']

        request = Mock()
        resource = Mock(actions=['index'])
        wrapper = ViewMapper(**{'attr': 'index'})(MyView)
        with pytest.raises(JHTTPBadRequest):
            wrapper(resource, request)

    def test_viewmapper_not_found(self):
        from nefertari.view import ViewMapper
        bc1 = Mock(side_effect=ResourceNotFound)

        class MyView(object):
            Model = 'foo'

            def __init__(self, ctx, req):
                self._before_calls = {'index': [bc1]}
                self._after_calls = {}
                self._json_params = {}
                self.context = 'foo'
                self.request = Mock(action='index')

            def index(self):
                return ['thing']

        request = Mock()
        resource = Mock(actions=['index'])
        wrapper = ViewMapper(**{'attr': 'index'})(MyView)
        with pytest.raises(JHTTPNotFound):
            wrapper(resource, request)


class TestBaseView(object):

    def get_common_mock_request(self):
        return Mock(content_type='', method='', accept=[''], user=None)

    def test_baseview(self, *a):

        class UsersView(BaseView):
            _json_encoder = _JSONEncoder

            def __init__(self, context, request):
                BaseView.__init__(self, context, request)
                self._json_params = {}
                self.context = 'foo'
                self.request = Mock(action='index')

            def show(self, id):
                return 'John Doe'

            def convert_ids2objects(self, *args, **kwargs):
                pass

        request = MagicMock(content_type='')
        request.matched_route.pattern = '/users'
        view = UsersView(request.context, request)

        assert 'John Doe' == view.show(1)

        with pytest.raises(JHTTPMethodNotAllowed):
            view.index()

        with pytest.raises(AttributeError):
            view.frobnicate()

        # delete is an allowed action, but it raises since BaseView
        # does not implement it.
        with pytest.raises(JHTTPMethodNotAllowed):
            view.delete()

    def test_convert_dotted(self):
        converted = BaseView.convert_dotted({
            'settings.foo': 'bar',
            'option': 'value',
            'one.two.three.four': 4,
            'one.two.six': 6,
        })
        assert sorted(converted.keys()) == sorted([
            'settings', 'option', 'one'])
        assert converted['settings'] == {'foo': 'bar'}
        assert converted['option'] == 'value'
        assert converted['one'] == {
            'two': {
                'three': {'four': 4},
                'six': 6,
            },
        }
        assert 'settings.foo' not in converted

    def test_convert_dotted_no_dotted(self):
        converted = BaseView.convert_dotted({
            'option': 'value'
        })
        assert converted == {'option': 'value'}

    @patch('nefertari.view.BaseView._run_init_actions')
    def test_init(self, run):
        request = Mock(
            content_type='application/json',
            json={'param1.foo': 'val1', 'param3': 'val3'},
            method='POST',
            accept=[''],
        )
        request.params.mixed.return_value = {'param2.foo': 'val2'}
        view = DummyBaseView(context={'foo': 'bar'}, request=request)
        run.assert_called_once_with()
        assert request.override_renderer == 'nefertari_json'
        assert list(sorted(view._params.keys())) == [
            'param1', 'param2', 'param3']
        assert view._params['param1'] == {'foo': 'val1'}
        assert view._params['param2'] == {'foo': 'val2'}
        assert view._params['param3'] == 'val3'
        assert view.request == request
        assert view.context == {'foo': 'bar'}
        assert view._before_calls == {}
        assert view._after_calls == {}

    @patch('nefertari.view.BaseView._run_init_actions')
    def test_init_json_accept_header(self, run):
        request = Mock(
            content_type='application/json',
            json={'param1.foo': 'val1', 'param3': 'val3'},
            method='POST',
            accept=['application/json'],
        )
        request.params.mixed.return_value = {'param2.foo': 'val2'}
        DummyBaseView(context={'foo': 'bar'}, request=request)
        assert request.override_renderer == 'nefertari_json'

    @patch('nefertari.view.BaseView._run_init_actions')
    def test_init_text_ct_and_accept(self, run):
        request = Mock(
            content_type='text/plain',
            json={'param1.foo': 'val1', 'param3': 'val3'},
            method='POST',
            accept=['text/plain'],
        )
        request.params.mixed.return_value = {'param2.foo': 'val2'}
        view = DummyBaseView(context={'foo': 'bar'}, request=request)
        assert request.override_renderer == 'string'
        assert list(view._params.keys()) == ['param2']

    @patch('nefertari.view.BaseView._run_init_actions')
    def test_init_json_error(self, run):
        import simplejson
        request = Mock(
            content_type='application/json',
            method='POST',
            accept=['application/json'],
        )
        type(request).json = PropertyMock(
            side_effect=simplejson.JSONDecodeError(
                'foo', 'asdasdasdasd', pos=1))
        request.params.mixed.return_value = {'param2.foo': 'val2'}
        view = DummyBaseView(context={'foo': 'bar'}, request=request)
        assert request.override_renderer == 'nefertari_json'
        assert list(view._params.keys()) == ['param2']

    @patch('nefertari.view.BaseView.setup_default_wrappers')
    @patch('nefertari.view.BaseView.convert_ids2objects')
    @patch('nefertari.view.BaseView.set_public_limits')
    def test_run_init_actions(self, limit, conv, setpub):
        request = Mock(
            content_type='text/plain',
            json={'param1.foo': 'val1', 'param3': 'val3'},
            method='POST',
            accept=['text/plain'],
        )
        request.params.mixed.return_value = {'param2.foo': 'val2'}
        DummyBaseView(context={'foo': 'bar'}, request=request)
        limit.assert_called_once_with()
        conv.assert_called_once_with()
        setpub.assert_called_once_with()

    @patch('nefertari.elasticsearch.ES')
    @patch('nefertari.view.ESAggregator')
    def test_setup_aggregation_es_disabled(self, aggregator, mock_es):
        mock_es.settings = dictset(enable_aggregations=False)
        request = Mock(content_type='', method='', accept=[''])
        view = DummyBaseView(context={}, request=request,
                        _query_params={'foo': 'bar'})
        view.index = 1
        view._setup_aggregation()
        assert view.index == 1

    @patch('nefertari.elasticsearch.ES')
    @patch('nefertari.view.ESAggregator')
    def test_setup_aggregation_index_not_defined(self, aggregator, mock_es):
        mock_es.settings = dictset(enable_aggregations=True)
        request = Mock(content_type='', method='', accept=[''])
        view = DummyBaseView(context={}, request=request,
                        _query_params={'foo': 'bar'})
        assert view.index == view.not_allowed_action
        view._setup_aggregation()
        with pytest.raises(JHTTPMethodNotAllowed):
            view.index()

    @patch('nefertari.elasticsearch.ES')
    @patch('nefertari.view.ESAggregator')
    def test_setup_aggregation(self, aggregator, mock_es):
        mock_es.settings = dictset(enable_aggregations=True)
        request = Mock(content_type='', method='', accept=[''])
        view = DummyBaseView(context={}, request=request,
                             _query_params={'foo': 'bar'})
        type(view).index = 1
        view._setup_aggregation()
        aggregator.assert_called_once_with(view)
        aggregator().wrap.assert_called_once_with(1)
        assert view.index == aggregator().wrap()

    @patch('nefertari.elasticsearch.ES')
    def test_get_collection_es(self, mock_es):
        request = Mock(content_type='', method='', accept=[''])
        view = DummyBaseView(
            context={}, request=request,
            _query_params={'foo': 'bar'})
        view.Model = Mock(__name__='MyModel')
        view._query_params['q'] = 'movies'
        result = view.get_collection_es()
        mock_es.assert_called_once_with('MyModel')
        mock_es().get_collection.assert_called_once_with(
            foo='bar', q='movies')
        assert result == mock_es().get_collection()

    @patch('nefertari.view.BaseView._run_init_actions')
    def test_fill_null_values(self, run):
        request = Mock(content_type='', method='', accept=[''])
        view = DummyBaseView(
            context={}, request=request,
            _query_params={'foo': 'bar'})
        view.Model = Mock()
        view.Model.get_null_values.return_value = {
            'name': None, 'email': 1, 'foo': None}
        view._json_params = {'foo': 'bar'}
        view.fill_null_values()
        assert view._json_params == {
            'foo': 'bar', 'name': None, 'email': 1
        }

    @patch('nefertari.view.BaseView._run_init_actions')
    def test_init_no_root(self, run):
        request = Mock(content_type='', method='', accept=[''])
        kwargs = dict(
            context={}, request=request, _query_params={'foo': 'bar'})
        view = DummyBaseView(**kwargs)
        view.root_resource = None
        view.__init__(**kwargs)
        assert not view._auth_enabled

    @patch('nefertari.view.wrappers')
    @patch('nefertari.view.BaseView._run_init_actions')
    def test_set_public_limits_no_auth(self, run, wrap):
        request = Mock(content_type='', method='', accept=[''])
        kwargs = dict(
            context={}, request=request, _query_params={'foo': 'bar'})
        view = DummyBaseView(**kwargs)
        view._auth_enabled = False
        view.set_public_limits()
        assert not wrap.set_public_limits.called

    @patch('nefertari.view.wrappers')
    @patch('nefertari.view.BaseView._run_init_actions')
    def test_set_public_limits_user_authenticated(self, run, wrap):
        request = Mock(content_type='', method='', accept=[''], user='foo')
        kwargs = dict(
            context={}, request=request, _query_params={'foo': 'bar'})
        view = DummyBaseView(**kwargs)
        view._auth_enabled = True
        view.set_public_limits()
        assert not wrap.set_public_limits.called

    @patch('nefertari.view.wrappers')
    @patch('nefertari.view.BaseView._run_init_actions')
    def test_set_public_limits_applied(self, run, wrap):
        request = self.get_common_mock_request()
        kwargs = dict(
            context={}, request=request, _query_params={'foo': 'bar'})
        view = DummyBaseView(**kwargs)
        view._auth_enabled = True
        view.set_public_limits()
        wrap.set_public_limits.assert_called_once_with(view)

    @patch('nefertari.view.engine')
    @patch('nefertari.view.BaseView.id2obj')
    @patch('nefertari.view.BaseView._run_init_actions')
    def test_convert_ids2objects_non_relational(self, run, id2obj, eng):
        request = self.get_common_mock_request()
        view = DummyBaseView(
            context={}, request=request, _query_params={'foo1': 'bar'},
            _json_params={'foo': 'bar'})
        view.Model = 'Model1'
        eng.is_relationship_field.return_value = False
        view.convert_ids2objects()
        eng.is_relationship_field.assert_called_once_with('foo', 'Model1')
        assert not id2obj.called

    @patch('nefertari.view.engine')
    @patch('nefertari.view.BaseView.id2obj')
    @patch('nefertari.view.BaseView._run_init_actions')
    def test_convert_ids2objects_relational(self, run, id2obj, eng):
        request = self.get_common_mock_request()
        view = DummyBaseView(
            context={}, request=request, _query_params={'foo1': 'bar'},
            _json_params={'foo': 'bar'})
        view.Model = 'Model1'
        eng.is_relationship_field.return_value = True
        view.convert_ids2objects()
        eng.get_relationship_cls.assert_called_once_with('foo', 'Model1')
        id2obj.assert_called_once_with('foo', eng.get_relationship_cls())

    @patch('nefertari.view.wrappers')
    @patch('nefertari.view.BaseView._run_init_actions')
    def test_setup_default_wrappers_with_auth(self, run, wrap):
        request = self.get_common_mock_request()
        view = DummyBaseView(
            context={}, request=request, _query_params={'foo': 'bar'})
        view._auth_enabled = True
        view.setup_default_wrappers()
        assert len(view._after_calls['index']) == 5
        assert len(view._after_calls['show']) == 4
        assert len(view._after_calls['create']) == 4
        assert len(view._after_calls['update']) == 4
        assert len(view._after_calls['replace']) == 4
        assert wrap.apply_privacy.call_count == 5

    @patch('nefertari.view.wrappers')
    @patch('nefertari.view.BaseView._run_init_actions')
    def test_setup_default_wrappers_no_auth(self, run, wrap):
        request = self.get_common_mock_request()
        view = DummyBaseView(
            context={}, request=request, _query_params={'foo': 'bar'})
        view._auth_enabled = False
        view.setup_default_wrappers()
        assert len(view._after_calls['index']) == 4
        assert len(view._after_calls['show']) == 3
        assert not wrap.apply_privacy.called

    def test_defalt_wrappers_and_wrap_me(self):
        from nefertari import wrappers

        self.maxDiff = None

        def before_call(*a):
            return a[2]

        def after_call(*a):
            return a[2]

        class MyView(BaseView):
            _json_encoder = _JSONEncoder

            @wrappers.wrap_me(before=before_call, after=after_call)
            def index(self):
                return [1, 2, 3]

            def convert_ids2objects(self, *args, **kwargs):
                pass

        request = MagicMock(content_type='')
        resource = MagicMock(actions=['index'])
        view = MyView(resource, request)

        assert len(view._after_calls['index']) == 4
        assert len(view._after_calls['show']) == 3

        assert view.index._before_calls == [before_call]
        assert view.index._after_calls == [after_call]

    @patch('nefertari.view.BaseView._run_init_actions')
    def test_not_allowed_action(self, run):
        request = self.get_common_mock_request()
        view = DummyBaseView(
            context={}, request=request, _query_params={'foo': 'bar'})
        with pytest.raises(JHTTPMethodNotAllowed):
            view.not_allowed_action()

    @patch('nefertari.view.BaseView._run_init_actions')
    def test_add_before_or_after_before(self, run):
        request = self.get_common_mock_request()
        view = DummyBaseView(
            context={}, request=request, _query_params={'foo': 'bar'})
        callable_ = lambda x: x
        view.add_before_or_after_call(
            action='foo', _callable=callable_, pos=None, before=True)
        assert callable_ in view._before_calls['foo']

    @patch('nefertari.view.BaseView._run_init_actions')
    def test_add_before_or_after_after(self, run):
        request = self.get_common_mock_request()
        view = DummyBaseView(
            context={}, request=request, _query_params={'foo': 'bar'})
        callable_ = lambda x: x
        view.add_before_or_after_call(
            action='foo', _callable=callable_, pos=None, before=False)
        assert callable_ in view._after_calls['foo']

    @patch('nefertari.view.BaseView._run_init_actions')
    def test_add_before_or_after_position(self, run):
        request = self.get_common_mock_request()
        view = DummyBaseView(
            context={}, request=request, _query_params={'foo': 'bar'})
        callable1 = lambda x: x
        callable2 = lambda x: x + x
        view.add_before_or_after_call(
            action='foo', _callable=callable1, pos=None,
            before=False)
        assert callable1 is view._after_calls['foo'][0]
        view.add_before_or_after_call(
            action='foo', _callable=callable2, pos=0,
            before=False)
        assert callable2 is view._after_calls['foo'][0]
        assert callable1 is view._after_calls['foo'][1]

    @patch('nefertari.view.BaseView._run_init_actions')
    def test_add_before_or_after_not_callable(self, run):
        request = self.get_common_mock_request()
        view = DummyBaseView(
            context={}, request=request, _query_params={'foo': 'bar'})
        with pytest.raises(ValueError) as ex:
            view.add_before_or_after_call(
                action='foo', _callable='asdasd', pos=None,
                before=False)
        assert str(ex.value) == 'asdasd is not a callable'

    @patch('nefertari.view.urllib')
    @patch('nefertari.view.Request')
    @patch('nefertari.view.BaseView._run_init_actions')
    def test_subrequest_get(self, run, req, ulib):
        request = Mock(
            content_type='', method='', accept=[''], user=None,
            cookies=['1'])
        view = DummyBaseView(
            context={}, request=request, _query_params={'foo': 'bar'})
        view.subrequest(url='http://', params={'par': 'val'}, method='GET')
        req.blank.assert_called_once_with(
            'http://', cookies=['1'], content_type='application/json',
            method='GET')
        view.request.invoke_subrequest.assert_called_once_with(req.blank())
        ulib.parse.urlencode.assert_called_once_with({'par': 'val'})

    @patch('nefertari.view.json')
    @patch('nefertari.view.Request')
    @patch('nefertari.view.BaseView._run_init_actions')
    def test_subrequest_post(self, run, req, json):
        request = Mock(
            content_type='', method='', accept=[''], user=None,
            cookies=['1'])
        view = DummyBaseView(
            context={}, request=request, _query_params={'foo': 'bar'})
        view.subrequest(url='http://', params={'par': 'val'}, method='POST')
        req.blank.assert_called_once_with(
            'http://', cookies=['1'], content_type='application/json',
            method='POST')
        view.request.invoke_subrequest.assert_called_once_with(req.blank())
        json.dumps.assert_called_once_with({'par': 'val'})

    @patch('nefertari.view.BaseView._run_init_actions')
    def test_id2obj(self, run):
        model = Mock()
        model.pk_field.return_value = 'idname'
        model.get_item.return_value = 'foo'
        request = self.get_common_mock_request()
        view = DummyBaseView(
            context={}, request=request, _json_params={'foo': 'bar'},
            _query_params={'foo1': 'bar1'})
        view._json_params['user'] = '1'
        view.id2obj(name='user', model=model)
        assert view._json_params['user'] == 'foo'
        model.pk_field.assert_called_once_with()
        model.get_item.assert_called_once_with(
            idname='1', __raise_on_empty=False)

    @patch('nefertari.view.BaseView._run_init_actions')
    def test_id2obj_list(self, run):
        model = Mock()
        model.pk_field.return_value = 'idname'
        model.get_item.return_value = 'foo'
        request = self.get_common_mock_request()
        view = DummyBaseView(
            context={}, request=request, _json_params={'foo': 'bar'},
            _query_params={'foo1': 'bar1'})
        view._json_params['user'] = ['1']
        view.id2obj(name='user', model=model)
        assert view._json_params['user'] == ['foo']
        model.pk_field.assert_called_once_with()
        model.get_item.assert_called_once_with(
            idname='1', __raise_on_empty=False)

    @patch('nefertari.view.BaseView._run_init_actions')
    def test_id2obj_not_in_params(self, run):
        model = Mock()
        request = self.get_common_mock_request()
        view = DummyBaseView(
            context={}, request=request, _json_params={'foo': 'bar'},
            _query_params={'foo1': 'bar1'})
        view.id2obj(name='asdasdasd', model=model)
        assert not model.pk_field.called
        assert not model.get_item.called

    @patch('nefertari.view.BaseView._run_init_actions')
    def test_id2obj_setdefault(self, run):
        model = Mock()
        model.pk_field.return_value = 'idname'
        model.get_item.return_value = None
        request = self.get_common_mock_request()
        view = DummyBaseView(
            context={}, request=request, _json_params={'foo': 'bar'},
            _query_params={'foo1': 'bar1'})
        view._json_params['user'] = '1'
        view.id2obj(name='user', model=model, setdefault=123)
        assert view._json_params['user'] == 123
        model.pk_field.assert_called_once_with()
        model.get_item.assert_called_once_with(
            idname='1', __raise_on_empty=False)

    @patch('nefertari.view.BaseView._run_init_actions')
    def test_id2obj_value_none(self, run):
        model = Mock()
        model.pk_field.return_value = 'idname'
        model.get_item.return_value = 'foo'
        request = self.get_common_mock_request()
        view = DummyBaseView(
            context={}, request=request, _json_params={'foo': 'bar'},
            _query_params={'foo1': 'bar1'})
        view._json_params['users'] = [None, '1']
        view._json_params['story'] = None
        view.id2obj(name='users', model=model)
        view.id2obj(name='story', model=model)
        assert view._json_params['users'] == [None, 'foo']
        assert view._json_params['story'] is None

    @patch('nefertari.view.BaseView._run_init_actions')
    def test_id2obj_already_object(self, run):
        id_ = Mock()
        model = Mock()
        model.pk_field.return_value = 'idname'
        model.get_item.return_value = None
        request = self.get_common_mock_request()
        view = DummyBaseView(
            context={}, request=request, _json_params={'foo': 'bar'},
            _query_params={'foo1': 'bar1'})
        view._json_params['user'] = id_
        view.id2obj(name='user', model=model, setdefault=123)
        assert view._json_params['user'] == id_
        model.pk_field.assert_called_once_with()
        assert not model.get_item.called

    @patch('nefertari.view.BaseView._run_init_actions')
    def test_id2obj_not_found(self, run):
        model = Mock()
        model.pk_field.return_value = 'idname'
        model.get_item.return_value = None
        request = self.get_common_mock_request()
        view = DummyBaseView(
            context={}, request=request, _json_params={'foo': 'bar'},
            _query_params={'foo1': 'bar1'})
        view._json_params['user'] = '1'
        with pytest.raises(JHTTPBadRequest) as ex:
            view.id2obj(name='user', model=model)
        assert str(ex.value) == 'id2obj: Object 1 not found'


class TestViewHelpers(object):
    def test_key_error_view(self):
        resp = key_error_view(Mock(args=('foo',)), None)
        assert str(resp.message) == "Bad or missing param 'foo'"

    def test_value_error_view(self):
        resp = value_error_view(Mock(args=('foo',)), None)
        assert str(resp.message) == "Bad or missing value 'foo'"

    def test_error_view(self):
        resp = error_view(Mock(args=('foo',)), None)
        assert str(resp.message) == "foo"

    def test_includeme(self):
        from nefertari.view import includeme
        config = Mock()
        includeme(config)
        calls = [
            call(key_error_view, context=KeyError),
            call(value_error_view, context=ValueError),
            call(error_view, context=Exception)
        ]
        config.add_view.assert_has_calls(calls, any_order=True)
