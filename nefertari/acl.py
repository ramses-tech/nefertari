from pyramid.security import ALL_PERMISSIONS, Allow, Everyone, Authenticated


class CopyACLMixin(object):
    """ ACL mixin that copies `self.__item_acl__` to
    `self.__context_class__.__item_acl__` """
    def __init__(self, request):
        model = self.__context_class__
        if model is not None and model.__item_acl__ is None:
            model.__item_acl__ = self.__item_acl__


class SelfParamMixin(object):
    """ ACL mixin that implements method to translate input key value
    to a user ID field, when key value equals :param_value:

    Value is only converted if user is logged in and :request.user:
    is an instance of :__context_class__:, thus for routes that display
    auth users.
    """
    param_value = 'self'

    def resolve_self_key(self, key):
        if key != self.param_value:
            return key
        user = getattr(self.request, 'user', None)
        if not user or not self.__context_class__:
            return key
        if not isinstance(user, self.__context_class__):
            return key
        obj_id = getattr(user, user.pk_field()) or key
        return obj_id


class BaseACL(CopyACLMixin, SelfParamMixin):
    """ Base ACL class.

    Grants:
        * all collection and item access to admins.
    """
    __context_class__ = None
    __item_acl__ = [(Allow, 'g:admin', ALL_PERMISSIONS)]

    def __init__(self, request):
        self.__acl__ = [(Allow, 'g:admin', ALL_PERMISSIONS)]
        self.request = request
        super(BaseACL, self).__init__(request)

    @property
    def acl(self):
        return self.__acl__

    @acl.setter
    def acl(self, val):
        assert(isinstance(val, tuple))
        self.__acl__.append(val)

    def __getitem__(self, key):
        assert(self.__context_class__)
        key = self.resolve_self_key(key)

        pk_field = self.__context_class__.pk_field()
        obj = self.__context_class__.get(
            __raise=True, **{pk_field: key})
        obj.__parent__ = self
        obj.__name__ = key
        return obj


class RootACL(CopyACLMixin):
    __acl__ = [
        (Allow, 'g:admin', ALL_PERMISSIONS),
    ]
    __item_acl__ = [
        (Allow, 'g:admin', ALL_PERMISSIONS),
    ]

    def __init__(self, request):
        self.request = request
        super(RootACL, self).__init__(request)


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
    __item_acl__ = [
        (Allow, 'g:admin', ALL_PERMISSIONS),
        (Allow, Everyone, ['show', 'item_options']),
    ]

    def __init__(self, request):
        super(GuestACL, self).__init__(request)
        self.acl = (Allow, Everyone, ['index', 'collection_options'])


class AuthenticatedReadACL(BaseACL):
    """ Authenticated users' ACL.

    Gives read access to all Authenticated users.
    Gives delete, create, update access to admin only.
    """
    __item_acl__ = [
        (Allow, 'g:admin', ALL_PERMISSIONS),
        (Allow, Authenticated, ['show', 'item_options']),
    ]

    def __init__(self, request):
        super(AuthenticatedReadACL, self).__init__(request)
        self.acl = (Allow, Authenticated, ['index', 'collection_options'])
