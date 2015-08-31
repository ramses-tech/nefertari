from mock import Mock

from nefertari import events


class TestEvents(object):
    def test_request_event_init(self):
        obj = events.RequestEvent(request=1, model=2, fields=3, field=4)
        assert obj.request == 1
        assert obj.model == 2
        assert obj.fields == 3
        assert obj.field == 4


class TestModelClassIs(object):
    def test_wrong_class(self):
        class A(object):
            pass

        predicate = events.ModelClassIs(model=A, config=None)
        event = events.before_index(request=None, model=list)
        assert not predicate(event)

    def test_correct_class(self):
        class A(object):
            pass

        predicate = events.ModelClassIs(model=A, config=None)
        event = events.before_index(request=None, model=A)
        assert predicate(event)

    def test_correct_subclass(self):
        class A(object):
            pass

        class B(A):
            pass

        predicate = events.ModelClassIs(model=A, config=None)
        event = events.before_index(request=None, model=B)
        assert predicate(event)


class TestFieldIsChanged(object):
    def test_field_changed(self):
        predicate = events.FieldIsChanged(field='username', config=None)
        event = events.before_index(
            request=None, model=None,
            fields={'username': 'asd'})
        assert event.field is None
        assert predicate(event)
        assert event.field == 'asd'

    def test_field_not_changed(self):
        predicate = events.FieldIsChanged(field='username', config=None)
        event = events.before_index(
            request=None, model=None,
            fields={'password': 'asd'})
        assert event.field is None
        assert not predicate(event)
        assert event.field is None
