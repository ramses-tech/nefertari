from contextlib import contextmanager

from nefertari.utils import FieldData


class RequestEvent(object):
    """ Nefertari request event.

    :param model: Model class affected by the request
    :param view: View instance which will process the request. Some
        useful attributes are: request, _json_params, _query_params.
        Change _json_params to edit data used to create/update objects
        and _query_params to edit data used to query database.
    :param fields: Dict of all fields from request.json. Keys are fields
        names and values are nefertari.utils.FieldData instances. If
        request does not have JSON body, value will be an empty dict.
    :param field: Changed field object. This field is set/changed in
        FieldIsChanged subscriber predicate. Do not use this field to
        determine what event was triggered when same event handler was
        registered with and without field predicate.
    :param instance: Object instance affected by request. Used in item
        requests  only. Should be used to read data only. Changes to the
        instance may result in database data inconsistency.
    """
    def __init__(self, model, view,
                 fields=None, field=None, instance=None):
        self.model = model
        self.view = view
        self.fields = fields
        self.field = field
        self.instance = instance

    def set_field_value(self, field_name, value):
        """ Set value of field named `field_name`.

        Use this method to apply changes to object which is affected
        by request. Values are set on `view._json_params` dict.

        If `field_name` is not affected by request, it is added to
        `self.fields` which makes field processors which are connected
        to `field_name` to be triggered, if they are run after this
        method call(connected to events after handler that performs
        method call).

        :param field_name: Name of field value of which should be set.
            Optional if `self.field` is set; in this case `self.field.name`
            is used. If `self.field` is None and `field_name` is not
            provided, KeyError is raised.
        :param value: Value to be set.
        """
        self.view._json_params[field_name] = value
        if field_name in self.fields:
            self.fields[field_name].new_value = value
            return

        fields = FieldData.from_dict({field_name: value}, self.model)
        self.fields.update(fields)


# 'Before' events

class BeforeIndex(RequestEvent):
    pass


class BeforeShow(RequestEvent):
    pass


class BeforeCreate(RequestEvent):
    pass


class BeforeUpdate(RequestEvent):
    pass


class BeforeReplace(RequestEvent):
    pass


class BeforeDelete(RequestEvent):
    pass


class BeforeUpdateMany(RequestEvent):
    pass


class BeforeDeleteMany(RequestEvent):
    pass


class BeforeItemOptions(RequestEvent):
    pass


class BeforeCollectionOptions(RequestEvent):
    pass


class BeforeLogin(RequestEvent):
    pass


class BeforeLogout(RequestEvent):
    pass


class BeforeRegister(RequestEvent):
    pass


# 'After' events

class AfterIndex(RequestEvent):
    pass


class AfterShow(RequestEvent):
    pass


class AfterCreate(RequestEvent):
    pass


class AfterUpdate(RequestEvent):
    pass


class AfterReplace(RequestEvent):
    pass


class AfterDelete(RequestEvent):
    pass


class AfterUpdateMany(RequestEvent):
    pass


class AfterDeleteMany(RequestEvent):
    pass


class AfterItemOptions(RequestEvent):
    pass


class AfterCollectionOptions(RequestEvent):
    pass


class AfterLogin(RequestEvent):
    pass


class AfterLogout(RequestEvent):
    pass


class AfterRegister(RequestEvent):
    pass


""" Events run before a particular event action happened.
It's recommended to use these events to:
    * Transform input
    * Perform validation
    * Apply changes to object that is being affected by request using
        `event.set_field_value`.
"""
BEFORE_EVENTS = {
    'index':                BeforeIndex,
    'show':                 BeforeShow,
    'create':               BeforeCreate,
    'update':               BeforeUpdate,
    'replace':              BeforeReplace,
    'delete':               BeforeDelete,
    'update_many':          BeforeUpdateMany,
    'delete_many':          BeforeDeleteMany,
    'item_options':         BeforeItemOptions,
    'collection_options':   BeforeCollectionOptions,

    'login':                BeforeLogin,
    'logout':               BeforeLogout,
    'register':             BeforeRegister,
}

""" Events run after a particular event action happened.
It's recommended to use these events to:
    * Change DB objects which are not affected by request.
    * Perform notifications/logging.
"""
AFTER_EVENTS = {
    'index':                AfterIndex,
    'show':                 AfterShow,
    'create':               AfterCreate,
    'update':               AfterUpdate,
    'replace':              AfterReplace,
    'delete':               AfterDelete,
    'update_many':          AfterUpdateMany,
    'delete_many':          AfterDeleteMany,
    'item_options':         AfterItemOptions,
    'collection_options':   AfterCollectionOptions,

    'login':                AfterLogin,
    'logout':               AfterLogout,
    'register':             AfterRegister,
}


# Subscriber predicates

class ModelClassIs(object):
    """ Subscriber predicate to check event.model is the right model.

    Example: config.add_subscriber(func, event, model=ModelCls)
    """

    def __init__(self, model, config):
        """
        :param model: Model class
        """
        self.model = model

    def text(self):
        return 'Model class is %s' % (self.model,)

    phash = text

    def __call__(self, event):
        """ Check whether one of following is true:

        * event.model is the same class as self.model
        * event.model is subclass of self.model
        """
        return issubclass(event.model, self.model)


class FieldIsChanged(object):
    """ Subscriber predicate to check particular field is changed.

    Used to implement field processors.
    """

    def __init__(self, field, config):
        self.field = field

    def text(self):
        return 'Field `%s` is changed' % (self.field,)

    phash = text

    def __call__(self, event):
        if self.field in event.fields:
            event.field = event.fields[self.field]
            return True
        return False


@contextmanager
def trigger_events(view_obj):
    """ Trigger before and after CRUD events.

    :param view_obj: Instance of nefertari.view.BaseView subclass created
        by nefertari.view.ViewMapper.
    """
    request = view_obj.request

    view_method = getattr(view_obj, request.action)
    event_action = (
        getattr(view_method, '_event_action', None) or
        request.action)

    do_trigger = not (
        getattr(view_method, '_silent', False) or
        getattr(view_obj, '_silent', False))

    if do_trigger:
        event_kwargs = {
            'view': view_obj,
            'model': view_obj.Model,
            'fields': FieldData.from_dict(
                view_obj._json_params,
                view_obj.Model)
        }
        if hasattr(view_obj.context, 'pk_field'):
            event_kwargs['instance'] = view_obj.context

        before_event = BEFORE_EVENTS[event_action]
        request.registry.notify(before_event(**event_kwargs))

    yield

    if do_trigger:
        after_event = AFTER_EVENTS[event_action]
        request.registry.notify(after_event(**event_kwargs))


def subscribe_to_events(config, subscriber, events, model=None):
    """ Helper function to subscribe to group of events.

    :param config: Pyramid contig instance.
    :param subscriber: Event subscriber function.
    :param events: Sequence of events to subscribe to.
    :param model: Model predicate value.
    """
    kwargs = {}
    if model is not None:
        kwargs['model'] = model

    for evt in events:
        config.add_subscriber(subscriber, evt, **kwargs)


def add_field_processors(config, processors, model, field):
    """ Add processors for model field.

    Under the hood, regular nefertari event subscribed is created which
    calls field processors in order passed to this function.

    Processors are passed following params:

    * **new_value**: New value of of field.
    * **instance**: Instance affected by request. Is None when set of
      items is updated in bulk and when item is created.
    * **field**: Instance of nefertari.utils.data.FieldData instance
      containing data of changed field.
    * **request**: Current Pyramid Request instance.
    * **model**: Model class affected by request.
    * **event**: Underlying event object.

    Each processor must return processed value which is passed to next
    processor.

    :param config: Pyramid Congurator instance.
    :param processors: Sequence of processor functions.
    :param model: Model class for field if which processors are
        registered.
    :param field: Field name for which processors are registered.
    """
    before_change_events = (
        BeforeCreate,
        BeforeUpdate,
        BeforeReplace,
        BeforeUpdateMany,
        BeforeRegister,
    )

    def wrapper(event, _processors=processors, _field=field):
        proc_kw = {
            'new_value': event.field.new_value,
            'instance': event.instance,
            'field': event.field,
            'request': event.view.request,
            'model': event.model,
            'event': event,
        }
        for proc_func in _processors:
            proc_kw['new_value'] = proc_func(**proc_kw)

        event.field.new_value = proc_kw['new_value']
        event.set_field_value(_field, proc_kw['new_value'])

    for evt in before_change_events:
        config.add_subscriber(wrapper, evt, model=model, field=field)


def silent(obj):
    """ Mark view method or class as "silent" so events won't be fired.

    Should be used as decorator on view classes or methods.

    :param obj: Any object that allows attributes assignment. Should be
        either view method or view class.
    """
    obj._silent = True
    return obj


def trigger_instead(event_action):
    """ Specify action name to change event triggered by view method.

    In the example above ``MyView.index`` method will trigger before/after
    ``update`` events.

    .. code-block:: json

        class MyView(BaseView):
            @events.trigger_instead('update')
            def index(self):
                (...)

    :param event_action: Event action name which should be triggered
        instead of default one.
    """
    def wrapper(func):
        func._event_action = event_action
        return func
    return wrapper
