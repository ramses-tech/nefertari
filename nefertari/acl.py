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


class ItemACL(Contained):
    """Collection item Resource.

    Override ``db_class`` to specify a db class. Only necessary if you need
     to consult the db object to deterimine a custom acl.

    Override ``custom_acl`` to provide a custom acl per instance. You will
    most likely want to use the ``db_object`` method in your implementation
    of this method. If you don't override this method, then the class's
    ``__acl__`` is used. If the class doesn't define a ``__acl__``, then it
    inherits its parent acl.
    """
    db_class = None

    def __init__(self, request, name, parent):
        super(ItemACL, self).__init__(request, name, parent)
        acl = self.custom_acl()
        if acl is not None:
            self.__acl__ = acl

    def custom_acl(self):
        """Returns a custom __acl__ for this instance. Returns None if this
        instance doesn't need a custom acl.
        """
        return None

    def db_key(self, key):
        """Override this method to transform the db key, e.g. to support
        ``self`` as a key on user collections.
        """
        return key

    def db_object(self):
        """Get db object corresponding to this resource"""
        if self.db_class == None:
            raise Exception('No db class is defined')
        pk_field = self.db_class.pk_field()
        key = self.db_key(self.__name__)
        return self.db_class.get(
            __raise=True,
            **{pk_field: key}
            )


class ContainerACL(Contained):
    """Collection resource.

    Define a ``__acl__`` attribute on this class to define the container's
    permissions, and default child permissions. Inherits its acl from the
    root, if no acl is set.

    Override ``child_class`` to specify a different class for child resources.
    This is only necessary if items need to have a different acl from the
    collection.
    """
    child_class = ItemACL

    def __getitem__(self, key):
        return self.child_class(self.request, key, self)

def authenticated_userid(request):
    """Helper function that can be used in ``db_key`` to support `self`
    as a collection key.
    """
    user = request.user
    key = user.pk_field()
    return getattr(user, key)


# Example ACL classes
#

class RootACL(Contained):
    __acl__ = (
        (Allow, 'g:admin', ALL_PERMISSIONS),
    )

class AdminACL(ContainerACL):
    """Admin level ACL. Gives all access to all actions to admin.

    May be used as a default factory for root resource.
    """
    __acl__ = (
        (Allow, 'g:admin', ALL_PERMISSIONS),
    )


class GuestACL(ContainerACL):
    """Guest level ACL.

    Gives read permissions to everyone.
    """
    __acl__ = (
        (Allow, 'g:admin', ALL_PERMISSIONS),
        (Allow, Everyone, ('view', 'options')),
    )


class AuthenticatedReadACL(ContainerACL):
    """ Authenticated users' ACL.

    Gives read access to all Authenticated users.
    Gives delete, create, update access to admin only.
    """
    __acl__ = (
        (Allow, 'g:admin', ALL_PERMISSIONS),
        (Allow, Authenticated, ('view', 'options')),
    )


class AuthenticationACL(ContainerACL):
    """ Special ACL factory to be used with authentication views
    (login, logout, register, etc.)

    Allows create, view and option methods to everyone.
    """

    __acl__ = (
        (Allow, 'g:admin', ALL_PERMISSIONS),
        (Allow, Everyone, ('create', 'view', 'options')),
    )
