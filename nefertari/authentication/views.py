from pyramid.security import remember, forget

from nefertari.json_httpexceptions import (
    JHTTPFound, JHTTPConflict, JHTTPUnauthorized, JHTTPNotFound, JHTTPOk,
    JHTTPBadRequest)
from nefertari.view import BaseView
from .models import AuthUser


class TicketAuthenticationView(BaseView):
    """ View for auth operations to use with Pyramid ticket-based auth.
        `login` (POST): Login the user with 'login' and 'password'
        `logout`: Logout user
    """
    _model_class = AuthUser

    def register(self):
        """ Register new user by POSTing all required data.

        """
        user, created = self._model_class.create_account(
            self._json_params)

        if not created:
            raise JHTTPConflict('Looks like you already have an account.')

        pk_field = user.pk_field()
        headers = remember(self.request, getattr(user, pk_field))
        return JHTTPOk('Registered', headers=headers)

    def login(self, **params):
        self._json_params.update(params)
        next = self._query_params.get('next', '')
        login_url = self.request.route_url('login')
        if next.startswith(login_url):
            next = ''  # never use the login form itself as next

        unauthorized_url = self._query_params.get('unauthorized', None)
        success, user = self._model_class.authenticate_by_password(
            self._json_params)

        if success:
            pk_field = user.pk_field()
            headers = remember(self.request, getattr(user, pk_field))
            if next:
                raise JHTTPFound(location=next, headers=headers)
            else:
                return JHTTPOk('Logged in', headers=headers)
        if user:
            if unauthorized_url:
                return JHTTPUnauthorized(location=unauthorized_url+'?error=1')

            raise JHTTPUnauthorized('Failed to Login.')
        else:
            raise JHTTPNotFound('User not found')

    def logout(self):
        next = self._query_params.get('next')
        headers = forget(self.request)
        if next:
            return JHTTPFound(location=next, headers=headers)
        return JHTTPOk('Logged out', headers=headers)


class TokenAuthenticationView(BaseView):
    """ View for auth operations to use with
    `nefertari.authentication.policies.ApiKeyAuthenticationPolicy`
    token-based auth. Implements methods:
    """
    _model_class = AuthUser

    def register(self):
        """ Register a new user by POSTing all required data.

        User's `Authorization` header value is returned in `WWW-Authenticate`
        header.
        """
        user, created = self._model_class.create_account(self._json_params)
        if user.api_key is None:
            raise JHTTPBadRequest('Failed to generate ApiKey for user')

        if not created:
            raise JHTTPConflict('Looks like you already have an account.')

        headers = remember(self.request, user.username)
        return JHTTPOk('Registered', headers=headers)

    def claim_token(self, **params):
        """Claim current token by POSTing 'login' and 'password'.

        User's `Authorization` header value is returned in `WWW-Authenticate`
        header.
        """
        self._json_params.update(params)
        success, self.user = self._model_class.authenticate_by_password(
            self._json_params)

        if success:
            headers = remember(self.request, self.user.username)
            return JHTTPOk('Token claimed', headers=headers)
        if self.user:
            raise JHTTPUnauthorized('Wrong login or password')
        else:
            raise JHTTPNotFound('User not found')

    def reset_token(self, **params):
        """ Reset current token by POSTing 'login' and 'password'.

        User's `Authorization` header value is returned in `WWW-Authenticate`
        header.
        """
        response = self.claim_token(**params)
        if not self.user:
            return response

        self.user.api_key.reset_token()
        headers = remember(self.request, self.user.username)
        return JHTTPOk('Registered', headers=headers)
