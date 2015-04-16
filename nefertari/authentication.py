from zope.dottedname.resolve import resolve
from pyramid.authentication import CallbackAuthenticationPolicy

from nefertari import engine as eng


def apikey_model(user_model):
    model_name = user_model.__class__.__name__
    try:
        return eng.get_document_cls(model_name)
    except ValueError:
        pass

    fk_kwargs = {
        'ref_column': None,
    }
    if hasattr(user_model, '__tablename__'):
        fk_kwargs['ref_column'] = '.'.join([user_model.__tablename__, 'id'])

    class ApiKey(eng.BaseDocument):
        id = eng.IdField(primary_key=True)
        token = eng.StringField()
        user = eng.Relationship(
            document=model_name,
            backref_name='api_key', uselist=False)
        owner_id = eng.ForeignKeyField(
            ref_document=model_name,
            ref_column_typ=eng.IdField,
            **fk_kwargs)

    # TODO: Connect signals to create ApiKey on User creation


class ApiKeyAuthenticationPolicy(CallbackAuthenticationPolicy):

    def __init__(self, user_model, *args, **kwargs):
        if isinstance(user_model, basestring):
            user_model = resolve(user_model)
        self.user_model = user_model
        self.api_key_model = apikey_model(self.user_model)
        super(ApiKeyAuthenticationPolicy, self).__init__(*args, **kwargs)

    def remember(self, request, userid, **kw):
        # Get user
        api_key = 'ApiKey {}:{}'.format(username, token)
        return [('WWW-Authenticate', api_key)]

    def forget(self, request):
        """ Returns challenge headers. This should be attached to a response
        to indicate that credentials are required."""
        return [('WWW-Authenticate', 'ApiKey realm="%s"' % self.realm)]

    def unauthenticated_userid(self, request):
        """ The userid parsed from the ``Authorization`` request header."""
        credentials = self._get_credentials(request)
        if credentials:
            return credentials[0]

    def callback(self, username, request):
        credentials = self._get_credentials(request)
        if credentials:
            username, api_key = credentials
            return self.check(username, api_key, request)

    def _get_credentials(self, request):
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
