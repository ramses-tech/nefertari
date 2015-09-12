from contextlib import contextmanager


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

    def set_field_value(self, value, field_name=None):
        """ Set value of field named `field_name`.

        Use this method to apply changes to object which is affected
        by request. Values are set on `view._json_params` dict.

        :param value: Value to be set.
        :param field_name: Name of field value of which should be set.
            Optional if `self.field` is set; in this case `self.field.name`
            is used. If `self.field` is None and `field_name` is not
            provided, KeyError is raised.
        """
        if field_name is None:
            if self.field is None:
                raise KeyError('Field name is not specified')
            field_name = self.field.name
        self.view._json_params[field_name] = value


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


""" Events run before a particular event action happened.
It's recommended to use these events to:
    * Transform input
    * Perform validation
    * Apply changes to object that is being affected by request using
        `event.set_field_value`.
"""
BEFORE_EVENTS = {
    'index': BeforeIndex,
    'show': BeforeShow,
    'create': BeforeCreate,
    'update': BeforeUpdate,
    'replace': BeforeReplace,
    'delete': BeforeDelete,
    'update_many': BeforeUpdateMany,
    'delete_many': BeforeDeleteMany,
    'item_options': BeforeItemOptions,
    'collection_options': BeforeCollectionOptions,
}

""" Events run after a particular event action happened.
It's recommended to use these events to:
    * Change DB objects which are not affected by request.
    * Perform notifications/logging.
"""
AFTER_EVENTS = {
    'index': AfterIndex,
    'show': AfterShow,
    'create': AfterCreate,
    'update': AfterUpdate,
    'replace': AfterReplace,
    'delete': AfterDelete,
    'update_many': AfterUpdateMany,
    'delete_many': AfterDeleteMany,
    'item_options': AfterItemOptions,
    'collection_options': AfterCollectionOptions,
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

    Example: config.add_subscriber(func, event, field=field_name)
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
    """ Trigger before_ and after_ CRUD events.

    :param view_obj: Instance of nefertari.view.BaseView subclass created
        by nefertari.view.ViewMapper.
    """
    from nefertari.utils import FieldData
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
        if hasattr(view_obj.context, 'pk_field'):
            event_kwargs['instance'] = view_obj.context

        before_event = BEFORE_EVENTS[request.action]
        request.registry.notify(before_event(**event_kwargs))

    yield

    if do_trigger:
        after_event = AFTER_EVENTS[request.action]
        request.registry.notify(after_event(**event_kwargs))


def subscribe_to_events(config, subscriber, events, model=None, field=None):
    """ Helper function to subscribe to group of events.

    :param config: Pyramid contig instance.
    :param subscriber: Event subscriber function.
    :param events: Sequence of events to subscribe to.
    :param model: Model predicate value.
    :param field: Field predicate value.
    """
    kwargs = {}
    if model is not None:
        kwargs['model'] = model
    if field is not None:
        kwargs['field'] = field

    for evt in events:
        config.add_subscriber(subscriber, evt, **kwargs)


def silent(obj):
    """ Mark view method or class as "silent" so events won't be fired.

    Should be used as decorator on view classes or methods.

    :param obj: Any object that allows attributes assignment. Should be
        either view method or view class.
    """
    obj._silent = True
    return obj
