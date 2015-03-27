from pyramid.security import (ALL_PERMISSIONS, Allow, Everyone, Deny)

from nefertari.json_httpexceptions import JHTTPNotFound


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
        obj = self.__context_class__.get(**{id_field: key})
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


class AuthenticatedUserACLMixin(object):
    """ User level ACL mixin. Mix it with your ACL class that sets
    ``self.user`` to a currently authenticated user.

    Grants access:
        * collection 'create' to everyone.
        * item 'update', 'delete' to owner.
        * item 'index', 'show' to everyone.
    """
    def __init__(self, request):
        super(AuthenticatedUserACLMixin, self).__init__(request)
        self.acl = (Allow, Everyone, 'create')

    def context_acl(self, context):
        return [
            (Allow, str(context.id), 'update'),
            (Allow, Everyone, ['index', 'show']),
            (Deny, str(context.id), 'delete'),
        ]

    def __getitem__(self, key):
        if not self.user:
            raise JHTTPNotFound

        obj = self.user
        obj.__acl__ = self.context_acl(obj)
        obj.__parent__ = self
        obj.__name__ = key
        return obj
