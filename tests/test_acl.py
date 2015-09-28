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


class DummyModel(object):
    @staticmethod
    def pk_field():
        return 'id'
    @classmethod
    def get_item(cls, id, **kw):
        i = cls()
        i.id = id
        return i


class TestACLsUnit(object):

    def dummy_acl(self):
        class DummyACL(acl.CollectionACL):
            item_model = DummyModel
        return DummyACL

    def test_default_acl(self):
        acl = self.dummy_acl()
        obj = acl(request='foo')
        assert obj.__acl__ == (('Allow', 'g:admin', ALL_PERMISSIONS),)

    def test_inherit_acl(self):
        acl = self.dummy_acl()
        item = acl(request='foo')['name']
        assert getattr(item, '__acl__', None) == None

    def test_item(self):
        acl = self.dummy_acl()
        item = acl(request='foo')['item-id']
        assert item.id == 'item-id'
        assert isinstance(item, acl.item_model)

    def test_custom_acl(self):
        class DummyACL(acl.CollectionACL):
            item_model = DummyModel
            def item_acl(self, item):
                return (
                    (Allow, item.id, 'update'),
                    )
        r = DummyACL(request='foo')
        item = r['item-id']
        assert item.__acl__ == ((Allow, 'item-id', 'update'),)

    def test_db_id(self):
        class DummyACL(acl.CollectionACL):
            item_model = DummyModel
            def item_db_id(self, key):
                if key == 'self':
                    return 42
                return key
        r = DummyACL(request='foo')
        item = r['item-id']
        assert item.id == 'item-id'
        item = r['self']
        assert item.id == 42

    def test_self_db_id(self):
        from nefertari.acl import authenticated_userid
        class DBClass(object):
            @staticmethod
            def pk_field():
                return 'id'
            @staticmethod
            def get_item(id, **kw):
                return id
        class UserACL(acl.CollectionACL):
            item_model = DummyModel
            def item_db_id(self, key):
                if self.request.user is not None and key == 'self':
                    return authenticated_userid(self.request)
                return key
        user = Mock(username='user12')
        user.pk_field.return_value = 'username'
        req = Mock(user=user)
        obj = UserACL(request=req)['self']
        assert obj.id == 'user12'

    def test_item_404(self):
        class NotFoundModel(DummyModel):
            @staticmethod
            def get_item(id, **kw):
                raise AttributeError()
        class DummyACL(acl.CollectionACL):
            item_model = NotFoundModel
        with pytest.raises(KeyError):
            DummyACL(request='foo')['item-id']

    def test_rootacl(self):
        acl_obj = acl.RootACL(request='foo')
        assert acl_obj.__acl__ == ((Allow, 'g:admin', ALL_PERMISSIONS),)
        assert acl_obj.request == 'foo'

    def test_guestacl_acl(self):
        acl_obj = acl.GuestACL(request='foo')
        assert acl_obj.__acl__ == (
            (Allow, 'g:admin', ALL_PERMISSIONS),
            (Allow, Everyone, ('view', 'options'))
        )

    def test_authenticatedreadacl_acl(self):
        acl_obj = acl.AuthenticatedReadACL(request='foo')
        assert acl_obj.__acl__ == (
            (Allow, 'g:admin', ALL_PERMISSIONS),
            (Allow, Authenticated, ('view', 'options'))
        )
