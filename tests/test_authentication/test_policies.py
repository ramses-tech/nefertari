import pytest
from mock import Mock, patch, call

from nefertari import authentication as auth
from .fixtures import engine_mock


@patch('nefertari.authentication.policies.apikey_model')
class TestApiKeyAuthenticationPolicy(object):

    def test_init(self, mock_apikey, engine_mock):
        user_model = Mock()
        policy = auth.policies.ApiKeyAuthenticationPolicy(
            user_model=user_model, check='foo',
            credentials_callback='bar')
        assert not engine_mock.get_document_cls.called
        mock_apikey.assert_called_once_with(user_model)
        assert policy.check == 'foo'
        assert policy.credentials_callback == 'bar'

    def test_init_string_user_model(self, mock_apikey, engine_mock):
        policy = auth.policies.ApiKeyAuthenticationPolicy(
            user_model='User1', check='foo',
            credentials_callback='bar')
        engine_mock.get_document_cls.assert_called_once_with('User1')
        mock_apikey.assert_called_once_with(engine_mock.get_document_cls())
        assert policy.check == 'foo'
        assert policy.credentials_callback == 'bar'

    def test_remember(self, mock_apikey, engine_mock):
        policy = auth.policies.ApiKeyAuthenticationPolicy(
            user_model='User1', check='foo',
            credentials_callback='bar')
        policy.credentials_callback = lambda uname, req: 'token'
        headers = policy.remember(request=None, username='user1')
        assert headers == [('WWW-Authenticate', 'ApiKey user1:token')]

    def test_forget(self, mock_apikey, engine_mock):
        policy = auth.policies.ApiKeyAuthenticationPolicy(
            user_model='User1', check='foo',
            credentials_callback='bar')
        policy.realm = 'Foo'
        headers = policy.forget(request=None)
        assert headers == [('WWW-Authenticate', 'ApiKey realm="Foo"')]
