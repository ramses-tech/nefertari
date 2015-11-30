""" Events needed to sync secondary engine with primary engine. """


class ItemEvent(object):
    def __init__(self, item):
        self.item = item


class BulkEvent(object):
    def __init__(self, items):
        self.items = items


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
