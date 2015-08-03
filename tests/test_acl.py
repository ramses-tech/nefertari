import pytest
from mock import Mock
from pyramid.security import ALL_PERMISSIONS, Allow, Everyone, Authenticated

from nefertari import acl


class TestACLsUnit(object):

    def test_baseacl_init(self):
        acl_obj = acl.BaseACL(request='foo')
        assert acl_obj.request == 'foo'
        assert acl_obj.__acl__ == [(Allow, 'g:admin', ALL_PERMISSIONS)]
        assert acl_obj.__item_acl__ == [
            (Allow, 'g:admin', ALL_PERMISSIONS)]

    def test_baseacl_acl_getter(self):
        acl_obj = acl.BaseACL(request='foo')
        assert acl_obj.acl is acl_obj.__acl__
        assert acl_obj.acl == [(Allow, 'g:admin', ALL_PERMISSIONS)]

    def test_baseacl_acl_setter(self):
        acl_obj = acl.BaseACL(request='foo')
        assert acl_obj.acl == [(Allow, 'g:admin', ALL_PERMISSIONS)]
        ace = (Allow, Everyone, ['index', 'show'])
        with pytest.raises(AssertionError):
            acl_obj.acl = [ace]
        acl_obj.acl = ace
        assert acl_obj.acl == [(Allow, 'g:admin', ALL_PERMISSIONS), ace]

    def test_baseacl_getitem_no_context_cls(self):
        acl_obj = acl.BaseACL(request='foo')
        assert acl_obj.__context_class__ is None
        with pytest.raises(AssertionError):
            acl_obj.__getitem__('foo')

    def test_baseacl_getitem(self):
        acl_obj = acl.BaseACL(request='foo')
        clx_cls = Mock()
        clx_cls.pk_field.return_value = 'storyname'
        acl_obj.__context_class__ = clx_cls
        obj = acl_obj.__getitem__('foo')
        clx_cls.pk_field.assert_called_once_with()
        clx_cls.get.assert_called_once_with(
            __raise=True, storyname='foo')
        assert obj.__parent__ == acl_obj
        assert obj.__name__ == 'foo'

    def test_rootacl(self):
        acl_obj = acl.RootACL(request='foo')
        assert acl_obj.__acl__ == [(Allow, 'g:admin', ALL_PERMISSIONS)]
        assert acl_obj.request == 'foo'

    def test_adminacl(self):
        acl_obj = acl.AdminACL(request='foo')
        assert isinstance(acl_obj, acl.BaseACL)
        assert acl_obj['foo'] == 1
        assert acl_obj['qweoo'] == 1

    def test_guestacl_acl(self):
        acl_obj = acl.GuestACL(request='foo')
        assert acl_obj.acl == [
            (Allow, 'g:admin', ALL_PERMISSIONS),
            (Allow, Everyone, ['index', 'collection_options'])
        ]
        assert acl_obj.__item_acl__ == [
            (Allow, 'g:admin', ALL_PERMISSIONS),
            (Allow, Everyone, ['show', 'item_options']),
        ]

    def test_authenticatedreadacl_acl(self):
        acl_obj = acl.AuthenticatedReadACL(request='foo')
        assert acl_obj.acl == [
            (Allow, 'g:admin', ALL_PERMISSIONS),
            (Allow, Authenticated, ['index', 'collection_options'])
        ]
        assert acl_obj.__item_acl__ == [
            (Allow, 'g:admin', ALL_PERMISSIONS),
            (Allow, Authenticated, ['show', 'item_options']),
        ]


class TestSelfParamMixin(object):

    def test_resolve_self_key_wrong_key(self):
        obj = acl.SelfParamMixin()
        assert obj.param_value == 'self'
        assert obj.resolve_self_key('') == ''
        assert obj.resolve_self_key('foo') == 'foo'

    def test_resolve_self_key_user_not_logged_in(self):
        obj = acl.SelfParamMixin()
        obj.request = Mock(user=None)
        assert obj.resolve_self_key('self') == 'self'

    def test_resolve_self_key_no_model_Cls(self):
        obj = acl.SelfParamMixin()
        obj.__context_class__ = None
        obj.request = Mock(user=1)
        assert obj.resolve_self_key('self') == 'self'

    def test_resolve_self_key_user_wrong_class(self):
        obj = acl.SelfParamMixin()
        obj.__context_class__ = dict
        obj.request = Mock(user='a')
        assert obj.resolve_self_key('self') == 'self'

    def test_resolve_self_key(self):
        obj = acl.SelfParamMixin()
        obj.__context_class__ = Mock
        user = Mock(username='user12')
        user.pk_field.return_value = 'username'
        obj.request = Mock(user=user)
        assert obj.resolve_self_key('self') == 'user12'


class TestCopyACLMixin(object):
    class DemoACL(acl.CopyACLMixin):
        __context_class__ = Mock(__item_acl__=None)
        __item_acl__ = [(1, 2, 3)]

    def test_init(self):
        obj = self.DemoACL('Foo')
        assert obj.__item_acl__ == [(1, 2, 3)]
        assert obj.__context_class__.__item_acl__ == [(1, 2, 3)]
