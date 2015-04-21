from pyramid.security import remember, forget

from nefertari.json_httpexceptions import *
from nefertari.view import BaseView
from .models import AuthUser


class TicketAuthenticationView(BaseView):
    """ View for auth operations to use with Pyramid ticket-based auth.
    Implements methods:
        `register` (POST): Register new user
        `login` (POST): Login the user with 'login' and 'password'
        `logout`: Logout user
    """
    _model_class = AuthUser

    def register(self):
        user, created = self._model_class.create_account(self._params)

        if not created:
            raise JHTTPConflict('Looks like you already have an account.')

        return JHTTPOk('Registered')

    def login(self, **params):
        self._params.update(params)
        next = self._params.get('next', '')
        login_url = self.request.route_url('login')
        if next.startswith(login_url):
            next = ''  # never use the login form itself as next

        unauthorized_url = self._params.get('unauthorized', None)
        success, user = self._model_class.authenticate(self._params)

        if success:
            headers = remember(self.request, user.uid)
            if next:
                return JHTTPOk('Logged in', headers=headers)
            else:
                return JHTTPOk('Logged in', headers=headers)
        if user:
            if unauthorized_url:
                return JHTTPUnauthorized(location=unauthorized_url+'?error=1')

            raise JHTTPUnauthorized('Failed to Login.')
        else:
            raise JHTTPNotFound('User not found')

    def logout(self):
        headers = forget(self.request)
        return JHTTPOk('Logged out', headers=headers)


class TokenAuthenticationView(BaseView):
    """ View for auth operations to use with
    nefertari.ApiKeyAuthenticationPolicy token-based auth.
    Implements methods:
        `register` (POST): Register new user
        `claim_token` (POST): Claim current token by submitting 'login' and
          'password'
        `token_reset` (POST): Reset current token by submitting 'login'
          and 'password'
    """
    _model_class = AuthUser

    def register(self):
        user, created = self._model_class.create_account(self._params)

        if not created:
            raise JHTTPConflict('Looks like you already have an account.')

        headers = remember(self.request, user.uid)
        return JHTTPOk('Registered', headers=headers)

    def claim_token(self, **params):
        self._params.update(params)
        success, self.user = self._model_class.authenticate(self._params)

        if success:
            headers = remember(self.request, self.user.uid)
            return JHTTPOk('Token claimed', headers=headers)
        if self.user:
            raise JHTTPUnauthorized('Wrong login or password')
        else:
            raise JHTTPNotFound('User not found')

    def token_reset(self, **params):
        response = self.claim_token(**params)
        if not self.user:
            return response

        self.user.api_key.reset_token()
        headers = remember(self.request, self.user.uid)
        return JHTTPOk('Registered', headers=headers)
