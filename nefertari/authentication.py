from pyramid.authentication import BasicAuthAuthenticationPolicy


class ApiKeyAuthenticationPolicy(BasicAuthAuthenticationPolicy):

    def __init__(self, userid_callback, *args, **kwargs):
        self.userid_callback = userid_callback
        super(ApiKeyAuthenticationPolicy, self).__init__(*args, **kwargs)

    def remember(self, request, userid, **kw):
        username, token = self.userid_callback(userid)
        api_key = 'ApiKey {}:{}'.format(username, token)
        return [('WWW-Authenticate', api_key)]

    def forget(self, request):
        """ Returns challenge headers. This should be attached to a response
        to indicate that credentials are required."""
        return [('WWW-Authenticate', 'ApiKey realm="%s"' % self.realm)]

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
