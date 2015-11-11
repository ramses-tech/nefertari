from pyramid.security import(
    ALL_PERMISSIONS,
    Allow,
    Everyone,
    Authenticated,
    )


class Contained(object):
    """Contained base class resource

    Can inherit its acl from its parent.
    """

    def __init__(self, request, name='', parent=None):
        self.request = request
        self.__name__ = name
        self.__parent__ = parent


class CollectionACL(Contained):
    """Collection resource.

    You must specify the ``item_model``. It should be a nefertari.engine
    document class. It is the model class for collection items.

    Define a ``__acl__`` attribute on this class to define the container's
    permissions, and default child permissions. Inherits its acl from the
    root, if no acl is set.

    Override the `item_acl` method if you wish to provide custom acls for
    collection items.

    Override the `item_db_id` method if you wish to transform the collection
    item db id, e.g. to support a ``self`` item on a user collection.
    """

    __acl__ = (
        (Allow, 'g:admin', ALL_PERMISSIONS),
    )

    item_model = None

    def __getitem__(self, key):
        db_id = self.item_db_id(key)
        pk_field = self.item_model.pk_field()
        try:
            item = self.item_model.get_item(
                __raise=True, **{pk_field: db_id}
                )
        except AttributeError:
            # strangely we get an AttributeError when the item isn't found
            raise KeyError(key)
        acl = self.item_acl(item)
        if acl is not None:
            item.__acl__ = acl
        item.__parent__ = self
        item.__name__ = key
        return item

    def item_acl(self, item):
        return None

    def item_db_id(self, key):
        return key


def authenticated_userid(request):
    """Helper function that can be used in ``db_key`` to support `self`
    as a collection key.
    """
    user = getattr(request, 'user', None)
    key = user.pk_field()
    return getattr(user, key)


# Example ACL classes and base classes
#

class RootACL(Contained):
    __acl__ = (
        (Allow, 'g:admin', ALL_PERMISSIONS),
    )


class GuestACL(CollectionACL):
    """Guest level ACL base class

    Gives read permissions to everyone.
    """
    __acl__ = (
        (Allow, 'g:admin', ALL_PERMISSIONS),
        (Allow, Everyone, ('view', 'options')),
    )


class AuthenticatedReadACL(CollectionACL):
    """ Authenticated users ACL base class

    Gives read access to all Authenticated users.
    Gives delete, create, update access to admin only.
    """
    __acl__ = (
        (Allow, 'g:admin', ALL_PERMISSIONS),
        (Allow, Authenticated, ('view', 'options')),
    )


class AuthenticationACL(Contained):
    """ Special ACL factory to be used with authentication views
    (login, logout, register, etc.)

    Allows create, view and option methods to everyone.
    """

    __acl__ = (
        (Allow, 'g:admin', ALL_PERMISSIONS),
        (Allow, Everyone, ('create', 'view', 'options')),
    )
