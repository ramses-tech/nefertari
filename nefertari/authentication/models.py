import uuid
import logging

import cryptacular.bcrypt
from pyramid.security import authenticated_userid, forget

from nefertari.json_httpexceptions import *
from nefertari import engine
from nefertari.utils import dictset

log = logging.getLogger(__name__)
crypt = cryptacular.bcrypt.BCRYPTPasswordManager()


class AuthModelDefaultMixin(object):
    """ Mixin that implements all methods required for Ticket and Token
    auth systems to work.

    All implemented methods must me class methods.
    """
    @classmethod
    def get_resource(self, *args, **kwargs):
        return super(AuthModelDefaultMixin, self).get_resource(*args, **kwargs)

    @classmethod
    def id_field(self, *args, **kwargs):
        return super(AuthModelDefaultMixin, self).id_field(*args, **kwargs)

    @classmethod
    def get_or_create(self, *args, **kwargs):
        return super(AuthModelDefaultMixin, self).get_or_create(*args, **kwargs)

    @classmethod
    def is_admin(cls, user):
        """ Determine if :user: is an admin. Is used by `apply_privacy` wrapper.
        """
        return 'admin' in user.groups

    @classmethod
    def token_credentials(cls, username, request):
        """ Get api token for user with username of :username:

        Is used by Token-based auth as `credentials_callback` kwarg.
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
    def groups_by_token(cls, username, token, request):
        """ Get user's groups if user with :username: exists and his api key
        token equals to :token:

        Is used by Token-based authentication as `check` kwarg.
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

        Is used both by Token and Ticket-based auths (called from views).
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
    def groups_by_userid(cls, userid, request):
        """ Return group identifiers of user with id :userid:

        Is used by Ticket-based auth as `callback` kwarg.
        """
        try:
            user = cls.get_resource(**{cls.id_field(): userid})
        except Exception as ex:
            log.error(unicode(ex))
            forget(request)
        else:
            if user:
                return ['g:%s' % g for g in user.groups]

    @classmethod
    def create_account(cls, params):
        """ Create auth user instance with data from :params:.

        Is used by both Token and Ticket-based auths to register a user (
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
    def authuser_by_userid(cls, request):
        """ Get user by ID.

        Is used by Ticket-based auth. Is added as request method to populate
        `request.user`.
        """
        _id = authenticated_userid(request)
        if _id:
            return cls.get_resource(**{cls.id_field(): _id})

    @classmethod
    def authuser_by_name(cls, request):
        """ Get user by username

        Is used by Token-based auth. Is added as request method to populate
        `request.user`.
        """
        username = authenticated_userid(request)
        if username:
            return cls.get_resource(username=username)


def lower_strip(value):
    return (value or '').lower().strip()


def crypt_password(password):
    """ Crypt :password: if it's not crypted yet """
    if password and not crypt.match(password):
        password = unicode(crypt.encode(password))
    return password


class AuthUser(AuthModelDefaultMixin, engine.BaseDocument):
    """ Class that is meant to be User class in Auth system.

    Implements basic operations to support Pyramid Ticket-based and custom
    ApiKey token-based authentication.
    """
    __tablename__ = 'nefertari_authuser'

    id = engine.IdField(primary_key=True)
    username = engine.StringField(
        min_length=1, max_length=50, unique=True,
        required=True, processors=[lower_strip])
    email = engine.StringField(
        unique=True, required=True, processors=[lower_strip])
    password = engine.StringField(
        min_length=3, required=True, processors=[crypt_password])
    groups = engine.ListField(
        item_type=engine.StringField,
        choices=['admin', 'user'], default=['user'])


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
        return engine.get_document_cls('ApiKey')
    except ValueError:
        pass

    fk_kwargs = {
        'ref_column': None,
    }
    if hasattr(user_model, '__tablename__'):
        fk_kwargs['ref_column'] = '.'.join([
            user_model.__tablename__, user_model.id_field()])
        fk_kwargs['ref_column_type'] = user_model.id_field_type()

    class ApiKey(engine.BaseDocument):
        __tablename__ = 'nefertari_apikey'

        id = engine.IdField(primary_key=True)
        token = engine.StringField(default=apikey_token)
        user = engine.Relationship(
            document=user_model.__name__,
            uselist=False,
            backref_name='api_key',
            backref_uselist=False)
        user_id = engine.ForeignKeyField(
            ref_document=user_model.__name__,
            **fk_kwargs)

        def reset_token(self):
            self.update({'token': apikey_token()})
            return self.token

    # Setup ApiKey autogeneration on :user_model: creation
    ApiKey.autogenerate_for(user_model, 'user')

    return ApiKey
