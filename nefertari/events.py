from zope.interface import (
    Attribute,
    Interface,
)
from zope.interface import implementer


class IRequestEvent(Interface):
    request = Attribute('Current Pyramid request object')
    model = Attribute('Model class affected by the request')
    fields = Attribute(
        'Dict of all fields from request.json. Keys are fields names and'
        'values are nefertari.utils.FieldData instances. If request does '
        'not have JSON body, value will be an empty dict.')


@implementer(IRequestEvent)
class RequestEvent(object):
    """ Nefertari request event. """
    def __init__(self, request, model, fields=None):
        self.request = request
        self.model = model
        self.fields = fields


# 'Before' events

class before_index(RequestEvent):
    pass


class before_show(RequestEvent):
    pass


class before_create(RequestEvent):
    pass


class before_update(RequestEvent):
    pass


class before_replace(RequestEvent):
    pass


class before_delete(RequestEvent):
    pass


class before_update_many(RequestEvent):
    pass


class before_delete_many(RequestEvent):
    pass


class before_item_options(RequestEvent):
    pass


class before_collection_options(RequestEvent):
    pass


# 'After' events

class after_index(RequestEvent):
    pass


class after_show(RequestEvent):
    pass


class after_create(RequestEvent):
    pass


class after_update(RequestEvent):
    pass


class after_replace(RequestEvent):
    pass


class after_delete(RequestEvent):
    pass


class after_update_many(RequestEvent):
    pass


class after_delete_many(RequestEvent):
    pass


class after_item_options(RequestEvent):
    pass


class after_collection_options(RequestEvent):
    pass


# Subscriber predicates

class ModelClassIs(object):
    """ Subscriber predicate to check event.model is the right model. """

    def __init__(self, model, config):
        """
        :param model: Model class
        """
        self.model = model

    def text(self):
        return 'Model class is %s' % (self.model,)

    phash = text

    def __call__(self, event):
        return event.model is self.model


class FieldIsChanged(object):
    """ Subscriber predicate to check event.model is changed. """

    def __init__(self, field, config):
        self.field = field

    def text(self):
        return 'Field `%s` is changed' % (self.field,)

    phash = text

    def __call__(self, event):
        if self.field in event.fields:
            event.fields = {self.field: event.fields[self.field]}
            return True
        return False
