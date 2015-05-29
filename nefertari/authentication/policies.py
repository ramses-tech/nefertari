import six
from pyramid.authentication import CallbackAuthenticationPolicy

from nefertari import engine
from .models import create_apikey_model


class ApiKeyAuthenticationPolicy(CallbackAuthenticationPolicy):
    """ ApiKey authentication policy.

    Relies on `Authorization` header being used in request, e.g.:
        `Authorization: ApiKey username:token`

    To use this policy, instantiate it with required arguments, as described
    in `__init__` method and register it with Pyramid's
    `Configurator.set_authentication_policy`.

    You may also find useful `nefertari.authentication.views.
    TokenAuthenticationView`
    view which offers basic functionality to create, claim, and reset the
    token.
    """
    def __init__(self, user_model, check=None, credentials_callback=None):
        """ Init the policy.

        Arguments:
            :user_model: String name or class of a User model for which ApiKey
                model is to be generated
            :check: A callback passed the username, api_key and the request,
                expected to return None if user doesn't exist or a sequence of
                principal identifiers (possibly empty) if the user does exist.
                If callback is None, the username will be assumed to exist with
                no principals. Optional.
            :credentials_callback: A callback passed the username and current
                request, expected to return and user's api key.
                Is used to generate 'WWW-Authenticate' header with a value of
                valid 'Authorization' request header that should be used to
                perform requests.
        """
        self.user_model = user_model
        if isinstance(self.user_model, six.string_types):
            self.user_model = engine.get_document_cls(self.user_model)
        create_apikey_model(self.user_model)

        self.check = check
        self.credentials_callback = credentials_callback
        super(ApiKeyAuthenticationPolicy, self).__init__()

    def remember(self, request, username, **kw):
        """ Returns 'WWW-Authenticate' header with a value that should be used
        in 'Authorization' header.
        """
        if self.credentials_callback:
            token = self.credentials_callback(username, request)
            api_key = 'ApiKey {}:{}'.format(username, token)
            return [('WWW-Authenticate', api_key)]

    def forget(self, request):
        """ Returns challenge headers. This should be attached to a response
        to indicate that credentials are required."""
        return [('WWW-Authenticate', 'ApiKey realm="%s"' % self.realm)]

    def unauthenticated_userid(self, request):
        """ Username parsed from the ``Authorization`` request header."""
        credentials = self._get_credentials(request)
        if credentials:
            return credentials[0]

    def callback(self, username, request):
        """ Having :username: return user's identifiers or None. """
        credentials = self._get_credentials(request)
        if credentials:
            username, api_key = credentials
            if self.check:
                return self.check(username, api_key, request)

    def _get_credentials(self, request):
        """ Extract username and api key token from 'Authorization' header """
        authorization = request.headers.get('Authorization')
        if not authorization:
            return None
        try:
            authmeth, authbytes = authorization.split(' ', 1)
        except ValueError:  # not enough values to unpack
            return None
        if authmeth.lower() != 'apikey':
            return None

        if six.PY2 or isinstance(authbytes, bytes):
            try:
                auth = authbytes.decode('utf-8')
            except UnicodeDecodeError:
                auth = authbytes.decode('latin-1')
        else:
            auth = authbytes

        try:
            username, api_key = auth.split(':', 1)
        except ValueError:  # not enough values to unpack
            return None
        return username, api_key
