""" Events needed to sync secondary engine with primary engine. """


class ItemEvent(object):
    def __init__(self, item, request):
        self.item = item
        self.request = request


class BulkEvent(object):
    def __init__(self, items, request):
        self.items = items
        self.request = request


class ItemCreated(ItemEvent):
    pass


class ItemUpdated(ItemEvent):
    pass


class ItemDeleted(ItemEvent):
    pass


class BulkUpdated(BulkEvent):
    pass


class BulkDeleted(BulkEvent):
    pass
