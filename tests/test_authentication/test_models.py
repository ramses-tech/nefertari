import pytest
from mock import Mock, patch

from .fixtures import engine_mock
from nefertari.json_httpexceptions import JHTTPBadRequest


class TestModelHelpers(object):

    def test_lower_strip(self, engine_mock):
        from nefertari.authentication import models
        assert models.lower_strip('Foo   ') == 'foo'
        assert models.lower_strip(None) == ''

    def test_crypt_password(self, engine_mock):
        from nefertari.authentication import models
        encrypted = models.crypt_password('foo')
        assert models.crypt.match(encrypted)
        assert encrypted != 'foo'
        assert encrypted == models.crypt_password(encrypted)

    @patch('nefertari.authentication.models.uuid.uuid4')
    def test_apikey_token(self, mock_uuid, engine_mock):
        from nefertari.authentication import models
        mock_uuid.return_value = Mock(hex='foo-bar')
        assert models.apikey_token() == 'foobar'


mixin_path = 'nefertari.authentication.models.AuthModelDefaultMixin.'


class TestAuthModelDefaultMixin(object):
    def test_is_admin(self, engine_mock):
        from nefertari.authentication import models
        user = Mock(groups=['user'])
        assert not models.AuthModelDefaultMixin.is_admin(user)
        user = Mock(groups=['user', 'admin'])
        assert models.AuthModelDefaultMixin.is_admin(user)

    @patch(mixin_path + 'get_resource')
    def test_token_credentials(self, mock_res, engine_mock):
        from nefertari.authentication import models
        user = Mock()
        user.api_key.token = 'foo-token'
        mock_res.return_value = user
        token = models.AuthModelDefaultMixin.token_credentials('user1', 1)
        assert token == 'foo-token'
        mock_res.assert_called_once_with(username='user1')

    @patch(mixin_path + 'get_resource')
    def test_token_credentials_user_not_found(self, mock_res, engine_mock):
        from nefertari.authentication import models
        mock_res.return_value = None
        token = models.AuthModelDefaultMixin.token_credentials('user1', 1)
        assert token is None
        mock_res.assert_called_once_with(username='user1')

    @patch('nefertari.authentication.models.forget')
    @patch(mixin_path + 'get_resource')
    def test_token_credentials_query_error(
            self, mock_res, mock_forg, engine_mock):
        from nefertari.authentication import models
        mock_res.side_effect = Exception
        token = models.AuthModelDefaultMixin.token_credentials('user1', 1)
        assert token is None
        mock_res.assert_called_once_with(username='user1')
        mock_forg.assert_called_once_with(1)

    @patch(mixin_path + 'get_resource')
    def test_groups_by_token(self, mock_res, engine_mock):
        from nefertari.authentication import models
        user = Mock(groups=['admin', 'user'])
        user.api_key.token = 'token'
        mock_res.return_value = user
        groups = models.AuthModelDefaultMixin.groups_by_token(
            'user1', 'token', 1)
        assert groups == ['g:admin', 'g:user']
        mock_res.assert_called_once_with(username='user1')

    @patch(mixin_path + 'get_resource')
    def test_groups_by_token_user_not_found(self, mock_res, engine_mock):
        from nefertari.authentication import models
        mock_res.return_value = None
        groups = models.AuthModelDefaultMixin.groups_by_token(
            'user1', 'token', 1)
        assert groups is None
        mock_res.assert_called_once_with(username='user1')

    @patch(mixin_path + 'get_resource')
    def test_groups_by_token_wrong_token(self, mock_res, engine_mock):
        from nefertari.authentication import models
        user = Mock(groups=['admin', 'user'])
        user.api_key.token = 'dasdasd'
        mock_res.return_value = user
        groups = models.AuthModelDefaultMixin.groups_by_token(
            'user1', 'token', 1)
        assert groups is None
        mock_res.assert_called_once_with(username='user1')

    @patch('nefertari.authentication.models.forget')
    @patch(mixin_path + 'get_resource')
    def test_groups_by_token_query_error(
            self, mock_res, mock_forg, engine_mock):
        from nefertari.authentication import models
        mock_res.side_effect = Exception
        groups = models.AuthModelDefaultMixin.groups_by_token(
            'user1', 'token', 1)
        assert groups is None
        mock_res.assert_called_once_with(username='user1')
        mock_forg.assert_called_once_with(1)

    @patch(mixin_path + 'get_resource')
    def test_authenticate_by_password(self, mock_res, engine_mock):
        from nefertari.authentication import models
        user = Mock(password=models.crypt.encode('foo'))
        mock_res.return_value = user
        success, usr = models.AuthModelDefaultMixin.authenticate_by_password(
            {'login': 'user1', 'password': 'foo'})
        assert success
        assert user == usr
        mock_res.assert_called_once_with(username='user1')
        models.AuthModelDefaultMixin.authenticate_by_password(
            {'login': 'user1@example.com', 'password': 'foo'})
        mock_res.assert_called_with(email='user1@example.com')

    @patch(mixin_path + 'get_resource')
    def test_authenticate_by_password_not_found(self, mock_res, engine_mock):
        from nefertari.authentication import models
        mock_res.return_value = None
        success, usr = models.AuthModelDefaultMixin.authenticate_by_password(
            {'login': 'user1', 'password': 'foo'})
        assert not success
        assert usr is None
        mock_res.assert_called_once_with(username='user1')

    @patch(mixin_path + 'get_resource')
    def test_authenticate_by_password_pasword_not_matching(
            self, mock_res, engine_mock):
        from nefertari.authentication import models
        user = Mock(password=models.crypt.encode('foo'))
        mock_res.return_value = user
        success, usr = models.AuthModelDefaultMixin.authenticate_by_password(
            {'login': 'user1', 'password': 'asdasdasd'})
        assert not success
        assert user == usr
        mock_res.assert_called_once_with(username='user1')

    @patch(mixin_path + 'get_resource')
    def test_authenticate_by_password_exception(self, mock_res, engine_mock):
        from nefertari.authentication import models
        mock_res.side_effect = Exception
        success, usr = models.AuthModelDefaultMixin.authenticate_by_password(
            {'login': 'user1', 'password': 'asdasdasd'})
        assert not success
        assert usr is None
        mock_res.assert_called_once_with(username='user1')

    @patch(mixin_path + 'id_field')
    @patch(mixin_path + 'get_resource')
    def test_groups_by_userid(self, mock_res, mock_field, engine_mock):
        from nefertari.authentication import models
        mock_field.return_value = 'idid'
        user = Mock(groups=['admin', 'user'])
        mock_res.return_value = user
        groups = models.AuthModelDefaultMixin.groups_by_userid(
            'user1', 1)
        assert groups == ['g:admin', 'g:user']
        mock_res.assert_called_once_with(idid='user1')

    @patch(mixin_path + 'id_field')
    @patch(mixin_path + 'get_resource')
    def test_groups_by_userid_user_not_found(
            self, mock_res, mock_field, engine_mock):
        from nefertari.authentication import models
        mock_field.return_value = 'idid'
        mock_res.return_value = None
        groups = models.AuthModelDefaultMixin.groups_by_userid(
            'user1', 1)
        assert groups is None
        mock_res.assert_called_once_with(idid='user1')

    @patch('nefertari.authentication.models.forget')
    @patch(mixin_path + 'id_field')
    @patch(mixin_path + 'get_resource')
    def test_groups_by_userid_query_error(
            self, mock_res, mock_field, mock_forg, engine_mock):
        from nefertari.authentication import models
        mock_field.return_value = 'idid'
        mock_res.side_effect = Exception
        groups = models.AuthModelDefaultMixin.groups_by_userid(
            'user1', 1)
        assert groups is None
        mock_res.assert_called_once_with(idid='user1')
        mock_forg.assert_called_once_with(1)

    @patch(mixin_path + 'get_or_create')
    def test_create_account(self, mock_get, engine_mock):
        from nefertari.authentication import models
        models.AuthModelDefaultMixin.create_account(
            {'username': 1, 'password': 2, 'email': 3, 'foo': 4})
        mock_get.assert_called_once_with(
            email=3,
            defaults={'username': 1, 'password': 2, 'email': 3})

    @patch(mixin_path + 'get_or_create')
    def test_create_account_bad_request(self, mock_get, engine_mock):
        from nefertari.authentication import models
        mock_get.side_effect = JHTTPBadRequest
        with pytest.raises(JHTTPBadRequest) as ex:
            models.AuthModelDefaultMixin.create_account({'email': 3})
        assert str(ex.value) == 'Failed to create account.'
        mock_get.assert_called_once_with(email=3, defaults={'email': 3})

    @patch('nefertari.authentication.models.authenticated_userid')
    @patch(mixin_path + 'id_field')
    @patch(mixin_path + 'get_resource')
    def test_authuser_by_userid(
            self, mock_res, mock_id, mock_auth, engine_mock):
        from nefertari.authentication import models
        mock_auth.return_value = 123
        mock_id.return_value = 'idid'
        models.AuthModelDefaultMixin.authuser_by_userid(1)
        mock_auth.assert_called_once_with(1)
        mock_res.assert_called_once_with(idid=123)

    @patch('nefertari.authentication.models.authenticated_userid')
    @patch(mixin_path + 'id_field')
    @patch(mixin_path + 'get_resource')
    def test_authuser_by_userid_not_authenticated(
            self, mock_res, mock_id, mock_auth, engine_mock):
        from nefertari.authentication import models
        mock_auth.return_value = None
        mock_id.return_value = 'idid'
        models.AuthModelDefaultMixin.authuser_by_userid(1)
        mock_auth.assert_called_once_with(1)
        assert not mock_res.called

    @patch('nefertari.authentication.models.authenticated_userid')
    @patch(mixin_path + 'get_resource')
    def test_authuser_by_name(
            self, mock_res, mock_auth, engine_mock):
        from nefertari.authentication import models
        mock_auth.return_value = 'user1'
        models.AuthModelDefaultMixin.authuser_by_name(1)
        mock_auth.assert_called_once_with(1)
        mock_res.assert_called_once_with(username='user1')

    @patch('nefertari.authentication.models.authenticated_userid')
    @patch(mixin_path + 'get_resource')
    def test_authuser_by_name_not_authenticated(
            self, mock_res, mock_auth, engine_mock):
        from nefertari.authentication import models
        mock_auth.return_value = None
        models.AuthModelDefaultMixin.authuser_by_name(1)
        mock_auth.assert_called_once_with(1)
        assert not mock_res.called
