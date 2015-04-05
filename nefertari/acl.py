from pyramid.security import (
    ALL_PERMISSIONS, Allow, Everyone, Deny,
    Authenticated)


class BaseACL(object):
    """ Base ACL class.

    Grants:
        * all collection and item access to admins.
    """
    __context_class__ = None

    def __init__(self, request):
        self.__acl__ = [(Allow, 'g:admin', ALL_PERMISSIONS)]
        self.__context_acl__ = [(Allow, 'g:admin', ALL_PERMISSIONS)]
        self.request = request

    @property
    def acl(self):
        return self.__acl__

    @acl.setter
    def acl(self, val):
        assert(isinstance(val, tuple))
        self.__acl__.append(val)

    def context_acl(self, obj):
        return self.__context_acl__

    def __getitem__(self, key):
        assert(self.__context_class__)

        id_field = self.__context_class__.id_field()
        obj = self.__context_class__.get(
            __raise=True, **{id_field: key})
        obj.__acl__ = self.context_acl(obj)
        obj.__parent__ = self
        obj.__name__ = key
        return obj


class RootACL(object):
    __acl__ = [
        (Allow, 'g:admin', ALL_PERMISSIONS),
    ]

    def __init__(self, request):
        self.request = request


class AdminACL(BaseACL):
    """ Admin level ACL. Gives all access to all actions.

    May be used as a default factory for root resource.
    """
    def __getitem__(self, key):
        return 1


class GuestACL(BaseACL):
    """ Guest level ACL.

    Gives read permissions to everyone.
    """
    def __init__(self, request):
        super(GuestACL, self).__init__(request)
        self.acl = (Allow, Everyone, ['index', 'show'])

    def context_acl(self, context):
        return [
            (Allow, Everyone, ['index', 'show']),
        ]


class AuthenticatedReadACL(BaseACL):
    """ Authenticated users' ACL.

    Gives read access to all Authenticated users.
    Gives delete, create, update access to admin only.
    """

    def __init__(self, request):
        super(AuthenticatedReadACL, self).__init__(request)
        self.acl = (Allow, Authenticated, ['index', 'show'])

    def context_acl(self, context):
        return [
            (Allow, 'g:admin', ALL_PERMISSIONS),
            (Allow, Authenticated, ['index', 'show']),
        ]
