import pytest
from mock import Mock
from pyramid.security import (
    ALL_PERMISSIONS,
    Allow,
    Authenticated,
    Deny,
    Everyone,
    )

from nefertari import acl


class TestACLsUnit(object):

    def test_no_acl(self):
        obj = acl.ContainerACL(request='foo')
        assert getattr(obj, '__acl__', None) is None

        child = acl.ContainerACL(request='foo')['name']
        assert getattr(child, '__acl__', None) is None

        obj = acl.ItemACL(request='foo', name='name', parent=None)
        assert getattr(obj, '__acl__', None) is None

    def test_inherit_acl(self):
        obj = acl.ContainerACL(request='foo')
        obj.__acl__ = ((Allow, Everyone, ALL_PERMISSIONS),)
        child = obj['name']
        assert child.__parent__.__acl__ == obj.__acl__

    def test_child_class(self):
        class MyItem(acl.ItemACL):
            __acl__ = ((Allow, Everyone, ALL_PERMISSIONS),)
        class MyContainer(acl.ContainerACL):
            __acl__ = ((Deny, Everyone, ALL_PERMISSIONS),)
            child_class = MyItem

        obj = MyContainer(request='foo')
        child = obj['name']
        assert child.__acl__ == ((Allow, Everyone, ALL_PERMISSIONS),)
        assert child.__parent__.__acl__ != child.__acl__

    def test_custom_acl(self):
        class MyItem(acl.ItemACL):
            def custom_acl(self):
                return ((Allow, self.__name__, 'update'),)
        class MyContainer(acl.ContainerACL):
            child_class = MyItem

        obj = MyContainer(request='foo')
        child = obj['name']
        assert child.__acl__ == ((Allow, 'name', 'update'),)

    def test_rootacl(self):
        acl_obj = acl.RootACL(request='foo')
        assert acl_obj.__acl__ == ((Allow, 'g:admin', ALL_PERMISSIONS),)
        assert acl_obj.request == 'foo'

    def test_adminacl(self):
        acl_obj = acl.AdminACL(request='foo')
        #assert isinstance(acl_obj, acl.BaseACL)
        #assert acl_obj['foo'] == 1
        #assert acl_obj['qweoo'] == 1

    def test_guestacl_acl(self):
        acl_obj = acl.GuestACL(request='foo')
        assert acl_obj.__acl__ == (
            (Allow, 'g:admin', ALL_PERMISSIONS),
            (Allow, Everyone, ('view', 'options'))
        )

    def test_guestacl_context_acl(self):
        acl_obj = acl.GuestACL(request='foo')
        child = acl_obj['name']
        assert getattr(child, '__acl__', None) is None
        assert child.__parent__.__acl__ == (
            (Allow, 'g:admin', ALL_PERMISSIONS),
            (Allow, Everyone, ('view', 'options')),
        )

    def test_authenticatedreadacl_acl(self):
        acl_obj = acl.AuthenticatedReadACL(request='foo')
        assert acl_obj.__acl__ == (
            (Allow, 'g:admin', ALL_PERMISSIONS),
            (Allow, Authenticated, ('view', 'options'))
        )

    def test_authenticatedreadacl_context_acl(self):
        acl_obj = acl.AuthenticatedReadACL(request='foo')
        child =  acl_obj['asdasd']
        assert getattr(child, '__acl__', None) is None
        assert child.__parent__.__acl__ == (
            (Allow, 'g:admin', ALL_PERMISSIONS),
            (Allow, Authenticated, ('view', 'options')),
        )



class TestDBObject(object):

    def test_no_db_class(self):
        obj = acl.ItemACL(request=42, name='name', parent=None)
        with pytest.raises(Exception) as e:
            obj.db_object()
        assert str(e.value) == 'No db class is defined'

    def test_db_obj(self):
        class DBClass(object):
            @staticmethod
            def pk_field():
                return 'id'
            @staticmethod
            def get(id, **kw):
                return id
        class MyItem(acl.ItemACL):
            db_class = DBClass
        obj = MyItem(request=42, name='name', parent=None)
        assert obj.db_object() == 'name'

    def test_db_key(self):
        class DBClass(object):
            @staticmethod
            def pk_field():
                return 'id'
            @staticmethod
            def get(id, **kw):
                return id
        class MyItem(acl.ItemACL):
            db_class = DBClass
            def db_key(self, key):
                return key.capitalize()
        obj = MyItem(request=42, name='name', parent=None)
        assert obj.db_object() == 'Name'

    def test_self_db_key(self):
        from nefertari.acl import authenticated_userid
        class DBClass(object):
            @staticmethod
            def pk_field():
                return 'id'
            @staticmethod
            def get(id, **kw):
                return id
        class MyItem(acl.ItemACL):
            db_class = DBClass
            def db_key(self, key):
                return authenticated_userid(self.request)
        user = Mock(username='user12')
        user.pk_field.return_value = 'username'
        req = Mock(user=user)
        obj = MyItem(request=req, name='self', parent=None)
        assert obj.db_object() == 'user12'
