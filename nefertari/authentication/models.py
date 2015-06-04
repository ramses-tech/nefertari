import uuid
import logging

import cryptacular.bcrypt
from pyramid.security import authenticated_userid, forget

from nefertari.json_httpexceptions import JHTTPBadRequest
from nefertari import engine
from nefertari.utils import dictset

log = logging.getLogger(__name__)
crypt = cryptacular.bcrypt.BCRYPTPasswordManager()


class AuthModelDefaultMixin(object):
    """ Mixin that implements all methods required for Ticket and Token
    auth systems to work.

    All implemented methods must be class methods.
    """
    @classmethod
    def get_resource(self, *args, **kwargs):
        return super(AuthModelDefaultMixin, self).get_resource(
            *args, **kwargs)

    @classmethod
    def pk_field(self, *args, **kwargs):
        return super(AuthModelDefaultMixin, self).pk_field(*args, **kwargs)

    @classmethod
    def get_or_create(self, *args, **kwargs):
        return super(AuthModelDefaultMixin, self).get_or_create(
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
            user = cls.get_resource(username=username)
        except Exception as ex:
            log.error(unicode(ex))
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
            user = cls.get_resource(username=username)
        except Exception as ex:
            log.error(unicode(ex))
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
            user = cls.get_resource(**{key: login})
        except Exception as ex:
            log.error(unicode(ex))

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
            user = cls.get_resource(**{cls.pk_field(): userid})
        except Exception as ex:
            log.error(unicode(ex))
            forget(request)
        else:
            if user:
                return ['g:%s' % g for g in user.groups]

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
        _id = authenticated_userid(request)
        if _id:
            return cls.get_resource(**{cls.pk_field(): _id})

    @classmethod
    def get_authuser_by_name(cls, request):
        """ Get user by username

        Used by Token-based auth. Is added as request method to populate
        `request.user`.
        """
        username = authenticated_userid(request)
        if username:
            return cls.get_resource(username=username)


def lower_strip(instance, new_value):
    return (new_value or '').lower().strip()


def encrypt_password(instance, new_value):
    """ Crypt :new_value: if it's not crypted yet. """
    if new_value and not crypt.match(new_value):
        new_value = unicode(crypt.encode(new_value))
    return new_value


class AuthUser(AuthModelDefaultMixin, engine.BaseDocument):
    """ Class that is meant to be User class in Auth system.

    Implements basic operations to support Pyramid Ticket-based and custom
    ApiKey token-based authentication.
    """
    __tablename__ = 'nefertari_authuser'

    id = engine.IdField(primary_key=True)

    username = engine.StringField(
        min_length=1, max_length=50, unique=True, required=True,
        before_validation=[lower_strip])
    email = engine.StringField(
        unique=True, required=True,
        before_validation=[lower_strip])
    password = engine.StringField(
        min_length=3, required=True,
        after_validation=[encrypt_password])

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
