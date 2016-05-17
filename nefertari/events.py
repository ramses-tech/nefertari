from nefertari.utils import FieldData, DataProxy


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
        requests  only(item GET, PATCH, PUT, DELETE). Should be used
        to read data only. Changes to the instance may result in database
        data inconsistency.
    :param response: Return value of view method serialized into dict.
        E.g. if view method returns "1", value of event.response will
        be "1". Is None in all "before" events. Note that is not a Pyramid
        Response instance but the value returned by view method.
        May be useful to access newly created object on "create" action
        if it is returned by view method.
    """
    def __init__(self, model, view,
                 fields=None, field=None, instance=None,
                 response=None):
        self.model = model
        self.view = view
        self.fields = fields
        self.field = field
        self.instance = instance
        self.response = response


class BeforeEvent(RequestEvent):
    """ Base class for events fired before a request is processed.

    Allows editing of request data.
    """
    def set_field_value(self, field_name, value):
        """ Set value of request field named `field_name`.

        Use this method to apply changes to object which is affected
        by request. Values are set on `view._json_params` dict.

        If `field_name` is not affected by request, it is added to
        `self.fields` which makes field processors which are connected
        to `field_name` to be triggered, if they are run after this
        method call(connected to events after handler that performs
        method call).

        :param field_name: Name of request field value of which should
            be set.
        :param value: Value to be set.
        """
        self.view._json_params[field_name] = value
        if field_name in self.fields:
            self.fields[field_name].new_value = value
            return

        fields = FieldData.from_dict({field_name: value}, self.model)
        self.fields.update(fields)


class AfterEvent(RequestEvent):
    """ Base class for events fired after a request is processed.

    Allows editing of response data.
    """
    def set_field_value(self, field_name, value):
        """ Set value of response field named `field_name`.

        If response contains single item, its field is set.
        If response contains multiple items, all the items in response
        are edited.
        To edit response meta(e.g. 'count') edit response directly at
        `event.response`.

        :param field_name: Name of response field value of which should
            be set.
        :param value: Value to be set.
        """
        if self.response is None:
            return

        if 'data' in self.response:
            items = self.response['data']
        else:
            items = [self.response]

        for item in items:
            item[field_name] = value


# 'Before' events

class BeforeIndex(BeforeEvent):
    pass


class BeforeShow(BeforeEvent):
    pass


class BeforeCreate(BeforeEvent):
    pass


class BeforeUpdate(BeforeEvent):
    pass


class BeforeReplace(BeforeEvent):
    pass


class BeforeDelete(BeforeEvent):
    pass


class BeforeUpdateMany(BeforeEvent):
    pass


class BeforeDeleteMany(BeforeEvent):
    pass


class BeforeItemOptions(BeforeEvent):
    pass


class BeforeCollectionOptions(BeforeEvent):
    pass


class BeforeLogin(BeforeEvent):
    pass


class BeforeLogout(BeforeEvent):
    pass


class BeforeRegister(BeforeEvent):
    pass


# 'After' events

class AfterIndex(AfterEvent):
    pass


class AfterShow(AfterEvent):
    pass


class AfterCreate(AfterEvent):
    pass


class AfterUpdate(AfterEvent):
    pass


class AfterReplace(AfterEvent):
    pass


class AfterDelete(AfterEvent):
    pass


class AfterUpdateMany(AfterEvent):
    pass


class AfterDeleteMany(AfterEvent):
    pass


class AfterItemOptions(AfterEvent):
    pass


class AfterCollectionOptions(AfterEvent):
    pass


class AfterLogin(AfterEvent):
    pass


class AfterLogout(AfterEvent):
    pass


class AfterRegister(AfterEvent):
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


def _get_event_kwargs(view_obj):
    """ Helper function to get event kwargs.

    :param view_obj: Instance of View that processes the request.
    :returns dict: Containing event kwargs or None if events shouldn't
        be fired.
    """
    request = view_obj.request

    view_method = getattr(view_obj, request.action)
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
        ctx = view_obj.context
        if hasattr(ctx, 'pk_field') or isinstance(ctx, DataProxy):
            event_kwargs['instance'] = ctx
        return event_kwargs


def _get_event_cls(view_obj, events_map):
    """ Helper function to get event class.

    :param view_obj: Instance of View that processes the request.
    :param events_map: Map of events from which event class should be
        picked.
    :returns: Found event class.
    """
    request = view_obj.request
    view_method = getattr(view_obj, request.action)
    event_action = (
        getattr(view_method, '_event_action', None) or
        request.action)
    return events_map[event_action]


def _trigger_events(view_obj, events_map, additional_kw=None):
    """ Common logic to trigger before/after events.

    :param view_obj: Instance of View that processes the request.
    :param events_map: Map of events from which event class should be
        picked.
    :returns: Instance if triggered event.
    """
    if additional_kw is None:
        additional_kw = {}

    event_kwargs = _get_event_kwargs(view_obj)
    if event_kwargs is None:
        return

    event_kwargs.update(additional_kw)
    event_cls = _get_event_cls(view_obj, events_map)
    event = event_cls(**event_kwargs)
    view_obj.request.registry.notify(event)
    return event


def trigger_before_events(view_obj):
    """ Trigger `before` CRUD events.

    :param view_obj: Instance of nefertari.view.BaseView subclass created
        by nefertari.view.ViewMapper.
    :returns: Instance if triggered event.
    """
    return _trigger_events(view_obj, BEFORE_EVENTS)


def trigger_after_events(view_obj):
    """ Trigger `after` CRUD events.

    :param view_obj: Instance of nefertari.view.BaseView subclass created
        by nefertari.view.ViewMapper.
    :returns: Instance if triggered event.
    """
    return _trigger_events(
        view_obj, AFTER_EVENTS,
        {'response': view_obj._response})


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
