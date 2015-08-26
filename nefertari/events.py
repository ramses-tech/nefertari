from zope.interface import (
    Attribute,
    Interface,
)
from zope.interface import implementer


class IRequestEvent(Interface):
    request = Attribute('Current Pyramid request object')
    model = Attribute('Model class affected by the request')


@implementer(IRequestEvent)
class RequestEvent(object):
    def __init__(self, request, model=None):
        self.request = request
        self.model = model


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


class ModelClassIs(object):
    """ Subscriber predicate to check event.model is the right model. """
    def __init__(self, model, config):
        self.model = model

    def text(self):
        return 'Model class is %s' % (self.model,)

    phash = text

    def __call__(self, event):
        return event.model is self.model
