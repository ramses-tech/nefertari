import uuid

from pyramid.authentication import CallbackAuthenticationPolicy

from nefertari import engine as eng


def apikey_token():
    """ Generate ApiKey.token using uuid library. """
    return uuid.uuid4().hex.replace('-', '')


def apikey_model(user_model):
    """ Generate ApiKey model class and connect it with :user_model:.

    ApiKey is generated having relationship to user model class :user_model:
    and has One-to-One relationship with backreference.
    ApiKey is setup to be auto-generated when new :user_model: is created.

    Returns ApiKey document class. If ApiKey is already defined, it is not
    generated again.

    Arguments:
        :user_model: Class that represents user model for which api keys will
            be generated and with which ApiKey will have relationship.
    """
    try:
        return eng.get_document_cls('ApiKey')
    except ValueError:
        pass

    fk_kwargs = {
        'ref_column': None,
    }
    if hasattr(user_model, '__tablename__'):
        fk_kwargs['ref_column'] = '.'.join([user_model.__tablename__, 'id'])
        fk_kwargs['ref_column_type'] = eng.IdField

    class ApiKey(eng.BaseDocument):
        __tablename__ = 'nefertari_apikey'

        id = eng.IdField(primary_key=True)
        token = eng.StringField(default=apikey_token)
        user = eng.Relationship(
            document=user_model.__name__,
            uselist=False,
            backref_name='api_key',
            backref_uselist=False)
        user_id = eng.ForeignKeyField(
            ref_document=user_model.__name__,
            **fk_kwargs)

        def reset_token(self):
            self.update({'token': apikey_token()})
            return self.token

    ApiKey.autogenerate_for(user_model, 'user')

    return ApiKey


class ApiKeyAuthenticationPolicy(CallbackAuthenticationPolicy):
    """ ApiKey authentication policy.

    Relies of `Authorization` header being used on request, e.g.:
        `Authorization: ApiKey username:token`
    """
    def __init__(self, user_model, check=None, credentials_callback=None):
        """ Init the policy.

        Arguments:
            :user_model: String name or class of a User model for which ApiKey
                model to be generated
            :check: A callback passed the username, api_key and the request,
                expected to return None if user doesn't exist or a sequence of
                principal identifiers (possibly empty) if the user does exist.
                If callback is None, the userid will be assumed to exist with
                no principals. Optional.
            :credentials_callback: A callback passed the userid, expected to
                return tuple containing 2 elements: username and user's api key.
                Is used to generate 'WWW-Authenticate' header with a value of
                valid 'Authorization' request header that should be used to
                perform requests.
        """
        self.user_model = user_model
        if isinstance(self.user_model, basestring):
            self.user_model = eng.get_document_cls(self.user_model)
        apikey_model(self.user_model)

        self.check = check
        self.credentials_callback = credentials_callback
        super(ApiKeyAuthenticationPolicy, self).__init__()

    def remember(self, request, userid, **kw):
        """ Return 'WWW-Authenticate' header with a value that should be used
        in 'Authorization' header.
        """
        if self.credentials_callback:
            username, token = self.credentials_callback(userid, request)
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

        try:
            auth = authbytes.decode('utf-8')
        except UnicodeDecodeError:
            auth = authbytes.decode('latin-1')

        try:
            username, api_key = auth.split(':', 1)
        except ValueError:  # not enough values to unpack
            return None
        return username, api_key
