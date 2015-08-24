from pyramid.security import(
    ALL_PERMISSIONS,
    Allow,
    Everyone,
    Authenticated,
    )



class Contained(object):
    """
    Contained resource, which can inherit its acl from its parent.
    """

    def __init__(self, request, name='', parent=None):
        self.request = request
        self.__name__ = name
        self.__parent__ = parent


class ItemACL(Contained):
    """
    Collection item Resource.

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
        """
        Returns a custom __acl__ for this instance. Returns None if this
        instance doesn't need a custom acl.
        """
        return None

    def db_key(self, key):
        """
        Override this method to transform the db key, e.g. to support
        ``self`` as a key on user collections.
        """
        return key

    def db_object(self):
        """
        Get db object corresponding to this resource
        """
        if self.db_class == None:
            raise Exception('No db class is defined')
        pk_field = self.db_class.pk_field()
        key = self.db_key(self.__name__)
        return self.db_class.get(
            __raise=True,
            **{pk_field: key}
            )


class ContainerACL(Contained):
    """
    Collection resource.

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


# class SelfParamMixin(object):
#     """ ACL mixin that implements method to translate input key value
#     to a user ID field, when key value equals :param_value:

#     Value is only converted if user is logged in and :request.user:
#     is an instance of :__context_class__:, thus for routes that display
#     auth users.
#     """
#     param_value = 'self'

#     def resolve_self_key(self, key):
#         if key != self.param_value:
#             return key
#         user = getattr(self.request, 'user', None)
#         if not user or not self.__context_class__:
#             return key
#         if not isinstance(user, self.__context_class__):
#             return key
#         obj_id = getattr(user, user.pk_field()) or key
#         return obj_id

def authenticated_userid(request):
    """
    Helper function that can be used in ``db_key`` to support `self`
    as a collection key.
    """
    user = request.user
    key = user.pk_field()
    return getattr(user, key)

# class BaseACL(SelfParamMixin):
#     """ Base ACL class.

#     Grants:
#         * all collection and item access to admins.
#     """
#     __context_class__ = None

#     def __init__(self, request):
#         self.__acl__ = [(Allow, 'g:admin', ALL_PERMISSIONS)]
#         self.__context_acl__ = [(Allow, 'g:admin', ALL_PERMISSIONS)]
#         self.request = request

#     @property
#     def acl(self):
#         return self.__acl__

#     @acl.setter
#     def acl(self, val):
#         assert(isinstance(val, tuple))
#         self.__acl__.append(val)

#     def context_acl(self, obj):
#         return self.__context_acl__

#     def __getitem__(self, key):
#         assert(self.__context_class__)
#         key = self.resolve_self_key(key)

#         pk_field = self.__context_class__.pk_field()
#         obj = self.__context_class__.get(
#             __raise=True, **{pk_field: key})
#         obj.__acl__ = self.context_acl(obj)
#         obj.__parent__ = self
#         obj.__name__ = key
#         return obj


# class RootACL(object):
#     __name__ = ''
#     __parent__ = None
#     __acl__ = (
#         (Allow, 'g:admin', ALL_PERMISSIONS),
#     )

#     def __init__(self, request):
#         self.request = request


class RootACL(Contained):
    __acl__ = (
        (Allow, 'g:admin', ALL_PERMISSIONS),
    )

# class AdminACL(BaseACL):
#     """ Admin level ACL. Gives all access to all actions.

#     May be used as a default factory for root resource.
#     """
#     def __getitem__(self, key):
#         return 1

class AdminACL(ContainerACL):
    """ Admin level ACL. Gives all access to all actions to admin.

    May be used as a default factory for root resource.
    """

    # XXX not really sure what the __getitem__ -> 1 business is about,
    # need to clarify the purpose of this class

    __acl__ = (
        (Allow, 'g:admin', ALL_PERMISSIONS),
    )


# class GuestACL(BaseACL):
#     """ Guest level ACL.

#     Gives read permissions to everyone.
#     """
#     def __init__(self, request):
#         super(GuestACL, self).__init__(request)
#         self.acl = (
#             Allow, Everyone, ['index', 'show', 'collection_options',
#                               'item_options'])

#     def context_acl(self, obj):
#         return [
#             (Allow, 'g:admin', ALL_PERMISSIONS),
#             (Allow, Everyone, ['index', 'show', 'collection_options',
#                                'item_options']),
#         ]

class GuestACL(ContainerACL):
    """ Guest level ACL.

    Gives read permissions to everyone.
    """
    __acl__ = (
        (Allow, 'g:admin', ALL_PERMISSIONS),
        (Allow, Everyone, ('view', 'options')),
    )

# class AuthenticatedReadACL(BaseACL):
#     """ Authenticated users' ACL.

#     Gives read access to all Authenticated users.
#     Gives delete, create, update access to admin only.
#     """
#     def __init__(self, request):
#         super(AuthenticatedReadACL, self).__init__(request)
#         self.acl = (Allow, Authenticated, ['index', 'collection_options'])

#     def context_acl(self, obj):
#         return [
#             (Allow, 'g:admin', ALL_PERMISSIONS),
#             (Allow, Authenticated, ['show', 'item_options']),
#         ]

class AuthenticatedReadACL(ContainerACL):
    """ Authenticated users' ACL.

    Gives read access to all Authenticated users.
    Gives delete, create, update access to admin only.
    """
    __acl__ = (
        (Allow, 'g:admin', ALL_PERMISSIONS),
        (Allow, Authenticated, ('view', 'options')),
    )

# class AuthenticationACL(BaseACL):
#     """ Special ACL factory to be used with authentication views
#     (login, logout, register, etc.)

#     Allows 'create', 'show' and option methods to everyone.
#     """
#     def __init__(self, request):
#         super(AuthenticationACL, self).__init__(request)
#         self.acl = (Allow, Everyone, [
#             'create', 'show', 'collection_options', 'item_options'])

#     def context_acl(self, obj):
#         return [
#             (Allow, 'g:admin', ALL_PERMISSIONS),
#             (Allow, Everyone, [
#                 'create', 'show', 'collection_options', 'item_options']),
#         ]

class AuthenticationACL(ContainerACL):
    """ Special ACL factory to be used with authentication views
    (login, logout, register, etc.)

    Allows 'create', 'show' and option methods to everyone.
    """

    __acl__ = (
        (Allow, 'g:admin', ALL_PERMISSIONS),
        (Allow, Everyone, ('create', 'view', 'options')),
    )
