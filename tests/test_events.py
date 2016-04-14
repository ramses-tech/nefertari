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

    def test_before_event_set_field_value_field_present(self):
        view = Mock(_json_params={})
        event = events.BeforeEvent(
            view=view, model=None, field=None,
            fields={})
        event.fields['foo'] = Mock()
        event.set_field_value('foo', 2)
        assert view._json_params == {'foo': 2}
        assert event.fields['foo'].new_value == 2

    @patch('nefertari.events.FieldData')
    def test_before_event_set_field_value_field_not_present(self, mock_field):
        mock_field.from_dict.return_value = {'q': 1}
        view = Mock(_json_params={})
        event = events.BeforeEvent(
            view=view, model=None, field=None,
            fields={})
        assert 'foo' not in event.fields
        event.set_field_value('foo', 2)
        assert view._json_params == {'foo': 2}
        mock_field.from_dict.assert_called_once_with(
            {'foo': 2}, event.model)
        assert event.fields == {'q': 1}

    def test_after_event_set_field_value_none_resp(self):
        view = Mock(_json_params={})
        event = events.AfterEvent(
            model=None, view=view)
        event.set_field_value('foo', 3)
        assert event.response is None

    def test_after_event_set_field_value_single_item(self):
        view = Mock(_json_params={})
        event = events.AfterEvent(
            model=None, view=view,
            response={'foo': 1, 'bar': 2})
        event.set_field_value('foo', 3)
        assert event.response == {'foo': 3, 'bar': 2}

    def test_after_event_set_field_value_collection(self):
        view = Mock(_json_params={})
        event = events.AfterEvent(
            model=None, view=view,
            response={'data': [
                {'foo': 1, 'bar': 4},
                {'foo': 1, 'bar': 5},
            ]}
        )
        event.set_field_value('foo', 3)
        assert len(event.response['data']) == 2
        assert {'foo': 3, 'bar': 4} in event.response['data']
        assert {'foo': 3, 'bar': 5} in event.response['data']


class TestHelperFunctions(object):
    def test_get_event_kwargs_no_trigger(self):
        view = Mock(index=Mock(_silent=True), _silent=True)
        view.request = Mock(action='index')
        assert events._get_event_kwargs(view) is None

    @patch('nefertari.events.FieldData')
    def test_get_event_kwargs(self, mock_fd):
        view = Mock(index=Mock(_silent=False), _silent=False)
        view.request = Mock(action='index')
        kwargs = events._get_event_kwargs(view)
        mock_fd.from_dict.assert_called_once_with(
            view._json_params, view.Model)
        assert kwargs == {
            'fields': mock_fd.from_dict(),
            'instance': view.context,
            'model': view.Model,
            'view': view
        }

    def test_get_event_cls_event_action(self):
        index = Mock(_event_action='index')
        request = Mock(action='index')
        view = Mock(request=request, index=index)
        evt = events._get_event_cls(view, events.BEFORE_EVENTS)
        assert evt is events.BeforeIndex

    def test_get_event_cls(self):
        index = Mock(_event_action=None)
        request = Mock(action='index')
        view = Mock(request=request, index=index)
        evt = events._get_event_cls(view, events.AFTER_EVENTS)
        assert evt is events.AfterIndex

    @patch('nefertari.events._get_event_cls')
    @patch('nefertari.events._get_event_kwargs')
    def test_trigger_events_no_kw(self, mock_kw, mock_cls):
        mock_cls.return_value = events.AfterIndex
        view = Mock()
        mock_kw.return_value = None
        events._trigger_events(view, events.AFTER_EVENTS)
        assert not mock_cls.called
        mock_kw.assert_called_once_with(view)

    @patch('nefertari.events._get_event_cls')
    @patch('nefertari.events._get_event_kwargs')
    def test_trigger_events(self, mock_kw, mock_cls):
        view = Mock()
        mock_kw.return_value = {'foo': 1}
        res = events._trigger_events(view, events.AFTER_EVENTS, {'bar': 2})
        mock_kw.assert_called_once_with(view)
        mock_cls.assert_called_once_with(view, events.AFTER_EVENTS)
        evt = mock_cls()
        evt.assert_called_once_with(foo=1, bar=2)
        view.request.registry.notify.assert_called_once_with(evt())
        assert res == evt()

    @patch('nefertari.events._trigger_events')
    def test_trigger_before_events(self, mock_trig):
        view = Mock()
        res = events.trigger_before_events(view)
        mock_trig.assert_called_once_with(view, events.BEFORE_EVENTS)
        assert res == mock_trig()

    @patch('nefertari.events._trigger_events')
    def test_trigger_after_events(self, mock_trig):
        view = Mock()
        res = events.trigger_after_events(view)
        mock_trig.assert_called_once_with(
            view, events.AFTER_EVENTS, {'response': view._response})
        assert res == mock_trig()

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

    def test_trigger_instead_decorator(self):
        @events.trigger_instead('foobar')
        def foo():
            pass

        assert foo._event_action == 'foobar'

    def test_add_field_processors(self):
        event = Mock()
        event.field.new_value = 'admin'
        config = Mock()
        processor = Mock(return_value='user12')

        events.add_field_processors(
            config, [processor, processor],
            model='User', field='username')
        assert config.add_subscriber.call_count == 5
        assert not event.set_field_value.called
        assert not processor.called

        last_call = config.add_subscriber.mock_calls[0]
        wrapper = last_call[1][0]
        wrapper(event)
        event.set_field_value.assert_called_once_with(
            'username', 'user12')
        assert event.field.new_value == 'user12'

        processor.assert_has_calls([
            call(new_value='admin', instance=event.instance,
                 field=event.field, request=event.view.request,
                 model=event.model, event=event),
            call(new_value='user12', instance=event.instance,
                 field=event.field, request=event.view.request,
                 model=event.model, event=event),
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
