import uuid
import logging

import cryptacular.bcrypt
from pyramid.security import authenticated_userid, forget

from nefertari.json_httpexceptions import JHTTPBadRequest
from nefertari import engine
from nefertari.utils import dictset

log = logging.getLogger(__name__)
crypt = cryptacular.bcrypt.BCRYPTPasswordManager()


class AuthModelMethodsMixin(object):
    """ Mixin that implements all methods required for Ticket and Token
    auth systems to work.

    All implemented methods must be class methods.
    """
    @classmethod
    def get_item(self, *args, **kwargs):
        return super(AuthModelMethodsMixin, self).get_item(
            *args, **kwargs)

    @classmethod
    def pk_field(self, *args, **kwargs):
        return super(AuthModelMethodsMixin, self).pk_field(*args, **kwargs)

    @classmethod
    def get_or_create(self, *args, **kwargs):
        return super(AuthModelMethodsMixin, self).get_or_create(
            *args, **kwargs)

    @classmethod
    def is_admin(cls, user):
        """ Determine if :user: is an admin. Used by `apply_privacy` wrapper.
        """
        return 'admin' in user.groups

    @classmethod
    def get_token_credentials(cls, username, request):
        """ Get api token for user with username of :username:

        Used by Token-based auth as `credentials_callback` kwarg.
        """
        try:
            user = cls.get_item(username=username)
        except Exception as ex:
            log.error(str(ex))
            forget(request)
        else:
            if user:
                return user.api_key.token

    @classmethod
    def get_groups_by_token(cls, username, token, request):
        """ Get user's groups if user with :username: exists and their api key
        token equals :token:

        Used by Token-based authentication as `check` kwarg.
        """
        try:
            user = cls.get_item(username=username)
        except Exception as ex:
            log.error(str(ex))
            forget(request)
            return
        else:
            if user and user.api_key.token == token:
                return ['g:%s' % g for g in user.groups]

    @classmethod
    def authenticate_by_password(cls, params):
        """ Authenticate user with login and password from :params:

        Used both by Token and Ticket-based auths (called from views).
        """
        def verify_password(user, password):
            return crypt.check(user.password, password)

        success = False
        user = None
        login = params['login'].lower().strip()
        key = 'email' if '@' in login else 'username'
        try:
            user = cls.get_item(**{key: login})
        except Exception as ex:
            log.error(str(ex))

        if user:
            password = params.get('password', None)
            success = (password and verify_password(user, password))
        return success, user

    @classmethod
    def get_groups_by_userid(cls, userid, request):
        """ Return group identifiers of user with id :userid:

        Used by Ticket-based auth as `callback` kwarg.
        """
        try:
            cache_request_user(cls, request, userid)
        except Exception as ex:
            log.error(str(ex))
            forget(request)
        else:
            if request._user:
                return ['g:%s' % g for g in request._user.groups]

    @classmethod
    def create_account(cls, params):
        """ Create auth user instance with data from :params:.

        Used by both Token and Ticket-based auths to register a user (
        called from views).
        """
        user_params = dictset(params).subset(
            ['username', 'email', 'password'])
        try:
            return cls.get_or_create(
                email=user_params['email'],
                defaults=user_params)
        except JHTTPBadRequest:
            raise JHTTPBadRequest('Failed to create account.')

    @classmethod
    def get_authuser_by_userid(cls, request):
        """ Get user by ID.

        Used by Ticket-based auth. Is added as request method to populate
        `request.user`.
        """
        userid = authenticated_userid(request)
        if userid:
            cache_request_user(cls, request, userid)
            return request._user

    @classmethod
    def get_authuser_by_name(cls, request):
        """ Get user by username

        Used by Token-based auth. Is added as request method to populate
        `request.user`.
        """
        username = authenticated_userid(request)
        if username:
            return cls.get_item(username=username)


def lower_strip(**kwargs):
    return (kwargs['new_value'] or '').lower().strip()


def random_uuid(**kwargs):
    return kwargs['new_value'] or uuid.uuid4().hex


def encrypt_password(**kwargs):
    """ Crypt :new_value: if it's not crypted yet. """
    new_value = kwargs['new_value']
    field = kwargs['field']
    min_length = field.params['min_length']
    if len(new_value) < min_length:
        raise ValueError(
            '`{}`: Value length must be more than {}'.format(
                field.name, field.params['min_length']))

    if new_value and not crypt.match(new_value):
        new_value = str(crypt.encode(new_value))
    return new_value


class AuthUserMixin(AuthModelMethodsMixin):
    """ Mixin that may be used as base for auth User models.

    Implements basic operations to support Pyramid Ticket-based and custom
    ApiKey token-based authentication.
    """
    username = engine.StringField(
        primary_key=True, unique=True,
        min_length=1, max_length=50)
    email = engine.StringField(unique=True, required=True)
    password = engine.StringField(min_length=3, required=True)
    groups = engine.ListField(
        item_type=engine.StringField,
        choices=['admin', 'user'], default=['user'])


def create_apikey_token():
    """ Generate ApiKey.token using uuid library. """
    return uuid.uuid4().hex.replace('-', '')


def create_apikey_model(user_model):
    """ Generate ApiKey model class and connect it with :user_model:.

    ApiKey is generated with relationship to user model class :user_model:
    as a One-to-One relationship with a backreference.
    ApiKey is set up to be auto-generated when a new :user_model: is created.

    Returns ApiKey document class. If ApiKey is already defined, it is not
    generated.

    Arguments:
        :user_model: Class that represents user model for which api keys will
            be generated and with which ApiKey will have relationship.
    """
    try:
        return engine.get_document_cls('ApiKey')
    except ValueError:
        pass

    fk_kwargs = {
        'ref_column': None,
    }
    if hasattr(user_model, '__tablename__'):
        fk_kwargs['ref_column'] = '.'.join([
            user_model.__tablename__, user_model.pk_field()])
        fk_kwargs['ref_column_type'] = user_model.pk_field_type()

    class ApiKey(engine.BaseDocument):
        __tablename__ = 'nefertari_apikey'

        id = engine.IdField(primary_key=True)
        token = engine.StringField(default=create_apikey_token)
        user = engine.Relationship(
            document=user_model.__name__,
            uselist=False,
            backref_name='api_key',
            backref_uselist=False)
        user_id = engine.ForeignKeyField(
            ref_document=user_model.__name__,
            **fk_kwargs)

        def reset_token(self):
            self.update({'token': create_apikey_token()})
            return self.token

    # Setup ApiKey autogeneration on :user_model: creation
    ApiKey.autogenerate_for(user_model, 'user')

    return ApiKey


def cache_request_user(user_cls, request, user_id):
    """ Helper function to cache currently logged in user.

    User is cached at `request._user`. Caching happens only only
    if user is not already cached or if cached user's pk does not
    match `user_id`.

    :param user_cls: User model class to use for user lookup.
    :param request: Pyramid Request instance.
    :user_id: Current user primary key field value.
    """
    pk_field = user_cls.pk_field()
    user = getattr(request, '_user', None)
    if user is None or getattr(user, pk_field, None) != user_id:
        request._user = user_cls.get_item(**{pk_field: user_id})
