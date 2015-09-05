import pytest
from mock import Mock, patch

from .fixtures import engine_mock
from nefertari.json_httpexceptions import JHTTPBadRequest
from nefertari.utils import FieldData


class TestModelHelpers(object):

    def test_lower_strip_with_value(self, engine_mock):
        from nefertari import events
        from nefertari.authentication import models
        field = FieldData(name='username', new_value='Foo            ')
        view = Mock(_json_params={})
        event = events.BeforeCreate(
            view=view, model=None, fields={},
            field=field)
        models.lower_strip(event)
        assert view._json_params == {'username': 'foo'}

    def test_lower_strip_without_value(self, engine_mock):
        from nefertari import events
        from nefertari.authentication import models
        field = FieldData(name='username', new_value=None)
        view = Mock(_json_params={})
        event = events.BeforeCreate(
            view=view, model=None, fields={}, field=field)
        models.lower_strip(event)
        assert view._json_params == {'username': ''}

    def test_encrypt_password(self, engine_mock):
        from nefertari import events
        from nefertari.authentication import models
        field = FieldData(
            name='password', new_value='foo',
            params={'min_length': 1})
        view = Mock(_json_params={'password': 'boo'})
        event = events.BeforeCreate(
            view=view, model=None, fields={}, field=field)

        models.encrypt_password(event)
        encrypted = event.view._json_params['password']
        assert models.crypt.match(encrypted)
        assert encrypted != 'foo'
        models.encrypt_password(event)
        assert encrypted == event.view._json_params['password']

    def test_encrypt_password_failed(self, engine_mock):
        from nefertari import events
        from nefertari.authentication import models
        field = FieldData(
            name='q', new_value='foo',
            params={'min_length': 10})
        view = Mock(_json_params={'password': 'boo'})
        event = events.BeforeCreate(
            view=view, model=None, fields={}, field=field)

        with pytest.raises(ValueError) as ex:
            models.encrypt_password(event)
        assert str(ex.value) == '`q`: Value length must be more than 10'

    @patch('nefertari.authentication.models.uuid.uuid4')
    def test_create_apikey_token(self, mock_uuid, engine_mock):
        from nefertari.authentication import models
        mock_uuid.return_value = Mock(hex='foo-bar')
        assert models.create_apikey_token() == 'foobar'

    def test_cache_request_user_not_present(self, engine_mock):
        from nefertari.authentication import models
        model_cls = Mock()
        model_cls.pk_field.return_value = 'myid'
        request = Mock(_user=None)
        models.cache_request_user(model_cls, request, 1)
        model_cls.get_resource.assert_called_once_with(myid=1)
        assert request._user == model_cls.get_resource()

    def test_cache_request_user_wrong_id(self, engine_mock):
        from nefertari.authentication import models
        model_cls = Mock()
        model_cls.pk_field.return_value = 'myid'
        request = Mock(_user=Mock(myid=4))
        models.cache_request_user(model_cls, request, 1)
        model_cls.get_resource.assert_called_once_with(myid=1)
        assert request._user == model_cls.get_resource()

    def test_cache_request_user_present(self, engine_mock):
        from nefertari.authentication import models
        model_cls = Mock()
        model_cls.pk_field.return_value = 'myid'
        request = Mock(_user=Mock(myid=1))
        models.cache_request_user(model_cls, request, 1)
        assert not model_cls.get_resource.called


mixin_path = 'nefertari.authentication.models.AuthModelMethodsMixin.'


class TestAuthModelMethodsMixin(object):
    def test_is_admin(self, engine_mock):
        from nefertari.authentication import models
        user = Mock(groups=['user'])
        assert not models.AuthModelMethodsMixin.is_admin(user)
        user = Mock(groups=['user', 'admin'])
        assert models.AuthModelMethodsMixin.is_admin(user)

    @patch(mixin_path + 'get_resource')
    def test_get_token_credentials(self, mock_res, engine_mock):
        from nefertari.authentication import models
        user = Mock()
        user.api_key.token = 'foo-token'
        mock_res.return_value = user
        token = models.AuthModelMethodsMixin.get_token_credentials('user1', 1)
        assert token == 'foo-token'
        mock_res.assert_called_once_with(username='user1')

    @patch(mixin_path + 'get_resource')
    def test_get_token_credentials_user_not_found(self, mock_res, engine_mock):
        from nefertari.authentication import models
        mock_res.return_value = None
        token = models.AuthModelMethodsMixin.get_token_credentials('user1', 1)
        assert token is None
        mock_res.assert_called_once_with(username='user1')

    @patch('nefertari.authentication.models.forget')
    @patch(mixin_path + 'get_resource')
    def test_get_token_credentials_query_error(
            self, mock_res, mock_forg, engine_mock):
        from nefertari.authentication import models
        mock_res.side_effect = Exception
        token = models.AuthModelMethodsMixin.get_token_credentials('user1', 1)
        assert token is None
        mock_res.assert_called_once_with(username='user1')
        mock_forg.assert_called_once_with(1)

    @patch(mixin_path + 'get_resource')
    def test_get_groups_by_token(self, mock_res, engine_mock):
        from nefertari.authentication import models
        user = Mock(groups=['admin', 'user'])
        user.api_key.token = 'token'
        mock_res.return_value = user
        groups = models.AuthModelMethodsMixin.get_groups_by_token(
            'user1', 'token', 1)
        assert groups == ['g:admin', 'g:user']
        mock_res.assert_called_once_with(username='user1')

    @patch(mixin_path + 'get_resource')
    def test_get_groups_by_token_user_not_found(self, mock_res, engine_mock):
        from nefertari.authentication import models
        mock_res.return_value = None
        groups = models.AuthModelMethodsMixin.get_groups_by_token(
            'user1', 'token', 1)
        assert groups is None
        mock_res.assert_called_once_with(username='user1')

    @patch(mixin_path + 'get_resource')
    def test_get_groups_by_token_wrong_token(self, mock_res, engine_mock):
        from nefertari.authentication import models
        user = Mock(groups=['admin', 'user'])
        user.api_key.token = 'dasdasd'
        mock_res.return_value = user
        groups = models.AuthModelMethodsMixin.get_groups_by_token(
            'user1', 'token', 1)
        assert groups is None
        mock_res.assert_called_once_with(username='user1')

    @patch('nefertari.authentication.models.forget')
    @patch(mixin_path + 'get_resource')
    def test_get_groups_by_token_query_error(
            self, mock_res, mock_forg, engine_mock):
        from nefertari.authentication import models
        mock_res.side_effect = Exception
        groups = models.AuthModelMethodsMixin.get_groups_by_token(
            'user1', 'token', 1)
        assert groups is None
        mock_res.assert_called_once_with(username='user1')
        mock_forg.assert_called_once_with(1)

    @patch(mixin_path + 'get_resource')
    def test_authenticate_by_password(self, mock_res, engine_mock):
        from nefertari.authentication import models
        user = Mock(password=models.crypt.encode('foo'))
        mock_res.return_value = user
        success, usr = models.AuthModelMethodsMixin.authenticate_by_password(
            {'login': 'user1', 'password': 'foo'})
        assert success
        assert user == usr
        mock_res.assert_called_once_with(username='user1')
        models.AuthModelMethodsMixin.authenticate_by_password(
            {'login': 'user1@example.com', 'password': 'foo'})
        mock_res.assert_called_with(email='user1@example.com')

    @patch(mixin_path + 'get_resource')
    def test_authenticate_by_password_not_found(self, mock_res, engine_mock):
        from nefertari.authentication import models
        mock_res.return_value = None
        success, usr = models.AuthModelMethodsMixin.authenticate_by_password(
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
        success, usr = models.AuthModelMethodsMixin.authenticate_by_password(
            {'login': 'user1', 'password': 'asdasdasd'})
        assert not success
        assert user == usr
        mock_res.assert_called_once_with(username='user1')

    @patch(mixin_path + 'get_resource')
    def test_authenticate_by_password_exception(self, mock_res, engine_mock):
        from nefertari.authentication import models
        mock_res.side_effect = Exception
        success, usr = models.AuthModelMethodsMixin.authenticate_by_password(
            {'login': 'user1', 'password': 'asdasdasd'})
        assert not success
        assert usr is None
        mock_res.assert_called_once_with(username='user1')

    @patch(mixin_path + 'pk_field')
    @patch('nefertari.authentication.models.cache_request_user')
    def test_get_groups_by_userid(self, mock_cache, mock_field, engine_mock):
        from nefertari.authentication import models
        mock_field.return_value = 'idid'
        user = Mock(groups=['admin', 'user'])
        request = Mock(_user=user)
        groups = models.AuthModelMethodsMixin.get_groups_by_userid(
            'user1', request)
        assert groups == ['g:admin', 'g:user']
        mock_cache.assert_called_once_with(
            models.AuthModelMethodsMixin, request, 'user1')

    @patch(mixin_path + 'pk_field')
    @patch(mixin_path + 'get_resource')
    def test_get_groups_by_userid_user_not_found(
            self, mock_res, mock_field, engine_mock):
        from nefertari.authentication import models
        mock_field.return_value = 'idid'
        mock_res.return_value = None
        groups = models.AuthModelMethodsMixin.get_groups_by_userid(
            'user1', 1)
        assert groups is None
        mock_res.assert_called_once_with(idid='user1')

    @patch('nefertari.authentication.models.forget')
    @patch(mixin_path + 'pk_field')
    @patch(mixin_path + 'get_resource')
    def test_get_groups_by_userid_query_error(
            self, mock_res, mock_field, mock_forg, engine_mock):
        from nefertari.authentication import models
        mock_field.return_value = 'idid'
        mock_res.side_effect = Exception
        groups = models.AuthModelMethodsMixin.get_groups_by_userid(
            'user1', 1)
        assert groups is None
        mock_res.assert_called_once_with(idid='user1')
        mock_forg.assert_called_once_with(1)

    @patch(mixin_path + 'get_or_create')
    def test_create_account(self, mock_get, engine_mock):
        from nefertari.authentication import models
        models.AuthModelMethodsMixin.create_account(
            {'username': 1, 'password': 2, 'email': 3, 'foo': 4})
        mock_get.assert_called_once_with(
            email=3,
            defaults={'username': 1, 'password': 2, 'email': 3})

    @patch(mixin_path + 'get_or_create')
    def test_create_account_bad_request(self, mock_get, engine_mock):
        from nefertari.authentication import models
        engine_mock.mock_add_spec([])
        mock_get.side_effect = JHTTPBadRequest
        with pytest.raises(JHTTPBadRequest) as ex:
            models.AuthModelMethodsMixin.create_account({'email': 3})
        assert str(ex.value) == 'Failed to create account.'
        mock_get.assert_called_once_with(email=3, defaults={'email': 3})

    @patch('nefertari.authentication.models.authenticated_userid')
    @patch('nefertari.authentication.models.cache_request_user')
    def test_get_authuser_by_userid(
            self, mock_cache, mock_auth, engine_mock):
        from nefertari.authentication import models
        mock_auth.return_value = 123
        request = Mock()
        models.AuthModelMethodsMixin.get_authuser_by_userid(request)
        mock_auth.assert_called_once_with(request)
        mock_cache.assert_called_once_with(
            models.AuthModelMethodsMixin, request, 123)

    @patch('nefertari.authentication.models.authenticated_userid')
    @patch('nefertari.authentication.models.cache_request_user')
    def test_get_authuser_by_userid_not_authenticated(
            self, mock_cache, mock_auth, engine_mock):
        from nefertari.authentication import models
        mock_auth.return_value = None
        models.AuthModelMethodsMixin.get_authuser_by_userid(1)
        mock_auth.assert_called_once_with(1)
        assert not mock_cache.called

    @patch('nefertari.authentication.models.authenticated_userid')
    @patch(mixin_path + 'get_resource')
    def test_get_authuser_by_name(
            self, mock_res, mock_auth, engine_mock):
        from nefertari.authentication import models
        mock_auth.return_value = 'user1'
        models.AuthModelMethodsMixin.get_authuser_by_name(1)
        mock_auth.assert_called_once_with(1)
        mock_res.assert_called_once_with(username='user1')

    @patch('nefertari.authentication.models.authenticated_userid')
    @patch(mixin_path + 'get_resource')
    def test_get_authuser_by_name_not_authenticated(
            self, mock_res, mock_auth, engine_mock):
        from nefertari.authentication import models
        mock_auth.return_value = None
        models.AuthModelMethodsMixin.get_authuser_by_name(1)
        mock_auth.assert_called_once_with(1)
        assert not mock_res.called
