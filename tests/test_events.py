import pytest
from mock import patch, Mock, call

from nefertari import events


class TestEvents(object):
    def test_request_event_init(self):
        obj = events.RequestEvent(
            view=1, model=2, fields=3, field=4, instance=5)
        assert obj.view == 1
        assert obj.model == 2
        assert obj.fields == 3
        assert obj.field == 4
        assert obj.instance == 5

    def test_set_field_value_field_name_provided(self):
        view = Mock(_json_params={})
        event = events.RequestEvent(
            view=view, model=None, field=None)
        event.set_field_value(2, 'foo')
        assert view._json_params == {'foo': 2}

    def test_set_field_value_no_field_name(self):
        from nefertari.utils import FieldData
        field = FieldData(name='foo', new_value=1)
        view = Mock(_json_params={})
        event = events.RequestEvent(
            view=view, model=None, field=field)
        event.set_field_value(2)
        assert view._json_params == {'foo': 2}

    def test_set_field_value_no_field_name_no_field(self):
        view = Mock(_json_params={})
        event = events.RequestEvent(
            view=view, model=None, field=None)
        with pytest.raises(KeyError) as ex:
            event.set_field_value(2)
        assert 'Field name is not specified' in str(ex.value)

    @patch('nefertari.utils.FieldData.from_dict')
    def test_trigger_events(self, mock_from):
        mock_after = Mock()
        mock_before = Mock()
        mock_from.return_value = {'foo': 1}
        ctx = Mock()
        view = Mock(
            request=Mock(action='index'),
            _json_params={'bar': 1},
            context=ctx,
            _silent=False)
        view.index._silent = False

        with patch.dict(events.BEFORE_EVENTS, {'index': mock_before}):
            with patch.dict(events.AFTER_EVENTS, {'index': mock_after}):
                with events.trigger_events(view):
                    pass

        mock_after.assert_called_once_with(
            fields={'foo': 1}, model=view.Model, instance=ctx,
            view=view)
        mock_before.assert_called_once_with(
            fields={'foo': 1}, model=view.Model, instance=ctx,
            view=view)
        view.request.registry.notify.assert_has_calls([
            call(mock_before()),
            call(mock_after()),
        ])
        mock_from.assert_called_once_with({'bar': 1}, view.Model)

    @patch('nefertari.utils.FieldData.from_dict')
    def test_trigger_events_silent_view(self, mock_from):
        class A(object):
            pass

        mock_after = Mock()
        mock_before = Mock()
        ctx = A()
        view = Mock(
            Model=A,
            request=Mock(action='index'),
            _json_params={'bar': 1},
            context=ctx,
            _silent=True)
        view.index._silent = False

        with patch.dict(events.BEFORE_EVENTS, {'index': mock_before}):
            with patch.dict(events.AFTER_EVENTS, {'index': mock_after}):
                with events.trigger_events(view):
                    pass

        assert not mock_after.called
        assert not mock_before.called
        assert not view.request.registry.notify.called
        assert not mock_from.called

    @patch('nefertari.utils.FieldData.from_dict')
    def test_trigger_events_silent_view_method(self, mock_from):
        class A(object):
            pass

        mock_after = Mock()
        mock_before = Mock()
        ctx = A()
        view = Mock(
            Model=A,
            request=Mock(action='index'),
            _json_params={'bar': 1},
            context=ctx,
            _silent=False)
        view.index._silent = True

        with patch.dict(events.BEFORE_EVENTS, {'index': mock_before}):
            with patch.dict(events.AFTER_EVENTS, {'index': mock_after}):
                with events.trigger_events(view):
                    pass

        assert not mock_after.called
        assert not mock_before.called
        assert not view.request.registry.notify.called
        assert not mock_from.called


class TestHelperFunctions(object):
    def test_subscribe_to_events(self):
        config = Mock()
        events.subscribe_to_events(
            config, 'foo', [1, 2], model=3)
        config.add_subscriber.assert_has_calls([
            call('foo', 1, model=3),
            call('foo', 2, model=3)
        ])

    def test_silent_decorator(self):
        @events.silent
        def foo():
            pass

        assert foo._silent

        @events.silent
        class Foo(object):
            pass

        assert Foo._silent

    def test_add_field_processors(self):
        event = Mock()
        event.field.new_value = 'admin'
        config = Mock()
        processor = Mock(return_value='user12')

        events.add_field_processors(
            config, [processor, processor],
            model='User', field='username')
        assert config.add_subscriber.call_count == 4
        assert not event.set_field_value.called
        assert not processor.called

        last_call = config.add_subscriber.mock_calls[0]
        wrapper = last_call[1][0]
        wrapper(event)
        event.set_field_value.assert_called_once_with(
            'user12', 'username')

        processor.assert_has_calls([
            call(new_value='admin', instance=event.instance,
                 field=event.field, request=event.view.request,
                 model=event.model),
            call(new_value='user12', instance=event.instance,
                 field=event.field, request=event.view.request,
                 model=event.model),
        ])


class TestModelClassIs(object):
    def test_wrong_class(self):
        class A(object):
            pass

        predicate = events.ModelClassIs(model=A, config=None)
        event = events.BeforeIndex(view=None, model=list)
        assert not predicate(event)

    def test_correct_class(self):
        class A(object):
            pass

        predicate = events.ModelClassIs(model=A, config=None)
        event = events.BeforeIndex(view=None, model=A)
        assert predicate(event)

    def test_correct_subclass(self):
        class A(object):
            pass

        class B(A):
            pass

        predicate = events.ModelClassIs(model=A, config=None)
        event = events.BeforeIndex(view=None, model=B)
        assert predicate(event)


class TestFieldIsChanged(object):
    def test_field_changed(self):
        predicate = events.FieldIsChanged(field='username', config=None)
        event = events.BeforeIndex(
            view=None, model=None,
            fields={'username': 'asd'})
        assert event.field is None
        assert predicate(event)
        assert event.field == 'asd'

    def test_field_not_changed(self):
        predicate = events.FieldIsChanged(field='username', config=None)
        event = events.BeforeIndex(
            view=None, model=None,
            fields={'password': 'asd'})
        assert event.field is None
        assert not predicate(event)
        assert event.field is None
