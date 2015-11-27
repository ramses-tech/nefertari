from mock import Mock, patch

from nefertari import polymorphic
from nefertari.renderers import _JSONEncoder


class TestPolymorphicHelperMixin(object):
    def test_get_collections(self):
        mixin = polymorphic.PolymorphicHelperMixin()
        mixin.request = Mock(matchdict={
            'collections': 'stories ,users,users/foo'})
        assert mixin.get_collections() == set(['stories', 'users'])

    def test_get_resources(self):
        mixin = polymorphic.PolymorphicHelperMixin()
        mixin.request = Mock()
        resource1 = Mock(collection_name='stories')
        resource2 = Mock(collection_name='foo')
        mixin.request.registry._model_collections = {
            'bar': resource1,
            'baz': resource2,
        }
        resources = mixin.get_resources(['stories'])
        assert resources == set([resource1])


class TestPolymorphicACL(object):

    @patch.object(polymorphic.PolymorphicACL, 'set_collections_acl')
    def test_init(self, mock_meth):
        polymorphic.PolymorphicACL(None)
        mock_meth.assert_called_once_with()

    @patch.object(polymorphic.PolymorphicACL, 'set_collections_acl')
    def test_get_least_permissions_aces_not_allowed(self, mock_meth):
        request = Mock()
        request.has_permission.return_value = False
        acl = polymorphic.PolymorphicACL(request)
        resource = Mock()
        resource.view._factory = Mock()
        assert acl._get_least_permissions_aces([resource]) is None
        resource.view._factory.assert_called_once_with(request)
        request.has_permission.assert_called_once_with(
            'view', resource.view._factory())

    @patch.object(polymorphic.PolymorphicACL, 'set_collections_acl')
    def test_get_least_permissions_aces_allowed(self, mock_meth):
        from pyramid.security import Allow
        request = Mock()
        request.has_permission.return_value = True
        request.effective_principals = ['user', 'admin']
        acl = polymorphic.PolymorphicACL(request)
        resource = Mock()
        resource.view._factory = Mock()
        aces = acl._get_least_permissions_aces([resource])
        resource.view._factory.assert_called_once_with(request)
        request.has_permission.assert_called_once_with(
            'view', resource.view._factory())
        assert len(aces) == 2
        assert (Allow, 'user', 'view') in aces
        assert (Allow, 'admin', 'view') in aces

    @patch.object(polymorphic.PolymorphicACL, '_get_least_permissions_aces')
    @patch.object(polymorphic.PolymorphicACL, 'get_resources')
    @patch.object(polymorphic.PolymorphicACL, 'get_collections')
    def test_set_collections_acl_no_aces(self, mock_coll, mock_res,
                                         mock_aces):
        from pyramid.security import DENY_ALL
        mock_coll.return_value = ['stories', 'users']
        mock_res.return_value = ['foo', 'bar']
        mock_aces.return_value = None
        acl = polymorphic.PolymorphicACL(None)
        assert len(acl.__acl__) == 2
        assert DENY_ALL == acl.__acl__[-1]
        mock_coll.assert_called_once_with()
        mock_res.assert_called_once_with(['stories', 'users'])
        mock_aces.assert_called_once_with(['foo', 'bar'])

    @patch.object(polymorphic.PolymorphicACL, '_get_least_permissions_aces')
    @patch.object(polymorphic.PolymorphicACL, 'get_resources')
    @patch.object(polymorphic.PolymorphicACL, 'get_collections')
    def test_set_collections_acl_has_aces(self, mock_coll, mock_res,
                                          mock_aces):
        from pyramid.security import Allow, DENY_ALL
        aces = [(Allow, 'foobar', 'dostuff')]
        mock_aces.return_value = aces
        acl = polymorphic.PolymorphicACL(None)
        assert len(acl.__acl__) == 3
        assert DENY_ALL == acl.__acl__[-1]
        assert aces[0] in acl.__acl__
        assert mock_coll.call_count == 1
        assert mock_res.call_count == 1
        assert mock_aces.call_count == 1


class TestPolymorphicESView(object):

    class DummyPolymorphicESView(polymorphic.PolymorphicESView):
        _json_encoder = _JSONEncoder

    def _dummy_view(self):
        request = Mock(content_type='', method='', accept=[''], user=None)
        return self.DummyPolymorphicESView(
            context={}, request=request,
            _json_params={'foo': 'bar'},
            _query_params={'foo1': 'bar1'})

    @patch.object(polymorphic.PolymorphicESView, 'determine_types')
    def test_ini(self, mock_det):
        from nefertari.utils import dictset
        mock_det.return_value = ['story', 'user']
        view = self._dummy_view()
        mock_det.assert_called_once_with()
        assert isinstance(view.Model, dictset)
        assert dict(view.Model) == {'__name__': 'story,user'}

    @patch.object(polymorphic.PolymorphicESView, 'determine_types')
    @patch.object(polymorphic.PolymorphicESView, 'set_public_limits')
    @patch.object(polymorphic.PolymorphicESView, 'setup_default_wrappers')
    def test_run_init_actions(self, mock_wraps, mock_lims, mock_det):
        self._dummy_view()
        mock_wraps.assert_called_once_with()
        mock_lims.assert_called_once_with()

    @patch.object(polymorphic.PolymorphicESView, 'get_resources')
    @patch.object(polymorphic.PolymorphicESView, 'get_collections')
    def test_determine_types(self, mock_coll, mock_res):
        mock_coll.return_value = ['stories', 'users']
        stories_res = Mock()
        stories_res.view.Model = Mock(
            __name__='StoryFoo', _index_enabled=True)
        users_res = Mock()
        users_res.view.Model = Mock(
            __name__='UserFoo', _index_enabled=False)
        mock_res.return_value = [stories_res, users_res]
        view = self._dummy_view()
        types = view.determine_types()
        assert types == ['StoryFoo']
        mock_coll.assert_called_with()
        mock_res.assert_called_with(['stories', 'users'])

    @patch.object(polymorphic.PolymorphicESView, 'get_collection_es')
    @patch.object(polymorphic.PolymorphicESView, 'determine_types')
    def test_index(self, mock_det, mock_get):
        view = self._dummy_view()
        response = view.index('foo')
        mock_get.assert_called_once_with()
        assert response == mock_get()
        assert view._query_params['_limit'] == 20
