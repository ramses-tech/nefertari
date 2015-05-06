from mock import Mock, patch

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

    def test_unauthenticated_userid(self, mock_apikey, engine_mock):
        policy = auth.policies.ApiKeyAuthenticationPolicy(
            user_model='User1', check='foo',
            credentials_callback='bar')
        policy._get_credentials = Mock()
        policy._get_credentials.return_value = ('user1', 'token')
        val = policy.unauthenticated_userid(request=1)
        policy._get_credentials.assert_called_once_with(1)
        assert val == 'user1'

    def test_callback_no_creds(self, mock_apikey, engine_mock):
        policy = auth.policies.ApiKeyAuthenticationPolicy(
            user_model='User1', check='foo',
            credentials_callback='bar')
        policy._get_credentials = Mock(return_value=None)
        policy.check = Mock()
        policy.callback('user1', 1)
        policy._get_credentials.assert_called_once_with(1)
        assert not policy.check.called

    def test_callback(self, mock_apikey, engine_mock):
        policy = auth.policies.ApiKeyAuthenticationPolicy(
            user_model='User1', check='foo',
            credentials_callback='bar')
        policy._get_credentials = Mock(return_value=('user1', 'token'))
        policy.check = Mock()
        policy.callback('user1', 1)
        policy._get_credentials.assert_called_once_with(1)
        policy.check.assert_called_once_with('user1', 'token', 1)

    def test_get_credentials_no_header(self, mock_apikey, engine_mock):
        policy = auth.policies.ApiKeyAuthenticationPolicy(
            user_model='User1', check='foo',
            credentials_callback='bar')
        request = Mock(headers={})
        assert policy._get_credentials(request) is None

    def test_get_credentials_wrong_header(self, mock_apikey, engine_mock):
        policy = auth.policies.ApiKeyAuthenticationPolicy(
            user_model='User1', check='foo',
            credentials_callback='bar')
        request = Mock(headers={'Authorization': 'foo'})
        assert policy._get_credentials(request) is None

    def test_get_credentials_not_apikey_header(self, mock_apikey, engine_mock):
        policy = auth.policies.ApiKeyAuthenticationPolicy(
            user_model='User1', check='foo',
            credentials_callback='bar')
        request = Mock(headers={'Authorization': 'foo bar'})
        assert policy._get_credentials(request) is None

    def test_get_credentials_not_full_token(self, mock_apikey, engine_mock):
        policy = auth.policies.ApiKeyAuthenticationPolicy(
            user_model='User1', check='foo',
            credentials_callback='bar')
        request = Mock(headers={'Authorization': 'ApiKey user1'})
        assert policy._get_credentials(request) is None

    def test_get_credentials(self, mock_apikey, engine_mock):
        policy = auth.policies.ApiKeyAuthenticationPolicy(
            user_model='User1', check='foo',
            credentials_callback='bar')
        request = Mock(headers={'Authorization': 'ApiKey user1:token'})
        assert policy._get_credentials(request) == ('user1', 'token')
