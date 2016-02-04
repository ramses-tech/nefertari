import logging
from hashlib import md5

import six
from nefertari import engine
from nefertari.utils import is_document, dictset


log = logging.getLogger(__name__)


class ValidationError(Exception):
    pass


class ResourceNotFound(Exception):
    pass


# Decorators


class wrap_me(object):
    """Base class for decorators used to add before and after calls.
    The callables are appended to the ``before`` or ``after`` lists,
    which are in turn injected into the method object being decorated.
    Method is returned without any side effects.
    """

    def __init__(self, before=None, after=None):
        self.before = (before if type(before)
                       is list else ([before] if before else []))
        self.after = (after if type(after)
                      is list else ([after] if after else []))

    def __call__(self, meth):
        if not hasattr(meth, '_before_calls'):
            meth._before_calls = []
        if not hasattr(meth, '_after_calls'):
            meth._after_calls = []

        meth._before_calls += self.before
        meth._after_calls += self.after

        return meth


class callable_base(object):
    """Base class for all before and after calls.
    ``__eq__`` method is overloaded in order to prevent duplicate callables
    of the same type.
    For example, you could have a before call ``pager`` which is called in
    the base class and also decorate the action with ``paginate``. ``__eq__``
    declares all same type callables to be the same.
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __eq__(self, other):
        "we only allow one instance of the same type of callable."
        return type(self) == type(other)


# After calls.

class obj2dict(object):
    """ Convert object to dictionary.

    Sequence of objects is converted to sequence of dicts.
    Conversion is performed by calling object's 'to_dict' method.
    """
    def __init__(self, request):
        self.request = request

    def __call__(self, **kwargs):
        '''converts objects in `result` into dicts'''
        from nefertari.utils import issequence
        result = kwargs['result']
        if isinstance(result, dict):
            return result

        _fields = kwargs.get('_fields', [])
        if hasattr(result, '_nefertari_meta'):
            _fields = result._nefertari_meta.get('fields', [])

        if hasattr(result, "to_dict"):
            return result.to_dict(_keys=_fields, request=self.request)

        elif issequence(result):
            # make sure its mutable, i.e list
            result = list(result)
            for ix, each in enumerate(result):
                result[ix] = obj2dict(self.request)(
                    _fields=_fields, result=each)

        return result


class apply_request_privacy(object):
    """ Apply privacy rules to request data.

    If request data contains fields user does not have access to,
    JHTTPForbidden exception is raised listing all forbidden fields.
    """
    def __init__(self, model_cls, request_data):
        """
        :param model_cls: Model class affected by request.
        :param request_data: Request data.
        """
        self.model_cls = model_cls
        self.request_data = request_data

    def __call__(self, **kwargs):
        from nefertari.utils import validate_data_privacy, dictset
        from nefertari.json_httpexceptions import JHTTPForbidden
        request = kwargs.pop('request')
        request_data = dictset(self.request_data)
        request_data['_type'] = self.model_cls.__name__

        try:
            validate_data_privacy(
                request, request_data,
                wrapper_kw={'drop_hidden': False})
        except ValidationError as ex:
            raise JHTTPForbidden(
                'Not enough permissions to update fields: {}'.format(ex))


class apply_privacy(object):
    """ Apply privacy rules to a JSON response.

    Passed 'result' kwarg's value may be a dictset or a collection JSON
    output which contains objects' data under 'data' key as a sequence of
    dictsets.

    Privacy is applied checking model's (got using '_type' key value) fields:
      * _public_fields: Fields visible to non-authenticated users.
      * _auth_fields: Fields visible to authenticated users.
      * _hidden_fields: Fields hidden if `self.drop_hidden`
        is True, otherwise shown to everyone.

    Admin can see all the fields. Whether user is admin, is checked by
    calling 'is_admin()' method on 'self.request.user'.

    If this wrapper is called without request, no filtering is performed.
    Fields visible to all types of users: '_self', '_type'.
    """
    def __init__(self, request):
        self.request = request

    def _filter_fields(self, data):
        if '_type' not in data:
            return data
        try:
            model_cls = engine.get_document_cls(data['_type'])
        except ValueError as ex:
            log.error(str(ex))
            return data

        public_fields = set(getattr(model_cls, '_public_fields', None) or [])
        auth_fields = set(getattr(model_cls, '_auth_fields', None) or [])
        hidden_fields = set(getattr(model_cls, '_hidden_fields', None) or [])
        fields = set(data.keys())

        user = getattr(self.request, 'user', None)
        if self.request:
            # User authenticated
            if user:
                # User not admin
                if not self.is_admin:
                    fields &= auth_fields

            # User not authenticated
            else:
                fields &= public_fields

            if self.drop_hidden:
                if not self.is_admin:
                    fields -= hidden_fields
            else:
                fields.update(hidden_fields)

        fields.update(['_type', '_pk', '_self'])
        if not isinstance(data, dictset):
            data = dictset(data)
        data = data.subset(fields)

        return self._apply_nested_privacy(data)

    def _apply_nested_privacy(self, data):
        """ Apply privacy to nested documents.

        :param data: Dict of data to which privacy is already applied.
        """
        kw = {
            'is_admin': self.is_admin,
            'drop_hidden': self.drop_hidden,
        }
        for key, val in data.items():
            if is_document(val):
                data[key] = apply_privacy(self.request)(result=val, **kw)
            elif isinstance(val, list) and val and is_document(val[0]):
                data[key] = [apply_privacy(self.request)(result=doc, **kw)
                             for doc in val]
        return data

    def __call__(self, **kwargs):
        from nefertari.utils import issequence
        result = kwargs['result']
        self.drop_hidden = kwargs.get('drop_hidden', True)

        if not isinstance(result, dict):
            return result
        data = result.get('data', result)

        if data and isinstance(data, (dict, list)):
            self.is_admin = kwargs.get('is_admin')
            if self.is_admin is None:
                user = getattr(self.request, 'user', None)
                self.is_admin = user is not None and type(user).is_admin(user)
            if issequence(data) and not isinstance(data, dict):
                kw = {
                    'is_admin': self.is_admin,
                    'drop_hidden': self.drop_hidden
                }
                data = [apply_privacy(self.request)(result=d, **kw)
                        for d in data]
            else:
                data = self._filter_fields(data)

        if 'data' in result:
            result['data'] = data
        else:
            result = data
        return result


class wrap_in_dict(object):
    """ Wraps 'result' kwarg value in dict.

    If object passed in 'result' kwarg has metadata in '_nefertari_meta'
    attribute, it's metadata is preserved and then applied if object
    is converted to a sequence of dicts.

    Conversion of object from 'result' kwargs is performed by calling
    `obj2dict` wrapper.
    """
    def __init__(self, request):
        self.request = request

    def __call__(self, **kwargs):
        """ If result is a list then wrap it in the dict. """
        result = kwargs['result']

        if hasattr(result, '_nefertari_meta'):
            _meta = result._nefertari_meta
        else:
            _meta = {}

        result = obj2dict(self.request)(**kwargs)

        if isinstance(result, dict):
            return result
        else:
            result = {"data": result}
            result.update(_meta)

        return result


class add_meta(object):
    """ Add metadata to results.

    In particular adds:
      * 'count': Number of results. Equals to number of objects in
        `result['data']`
    """
    def __init__(self, request):
        self.request = request

    def __call__(self, **kwargs):
        result = kwargs['result']
        try:
            result['count'] = len(result['data'])
        finally:
            return result


class add_object_url(object):
    """ Add '_self' to each object in results

    For each object in `result['data']` fetches a uri from pyramid
    which points to current object
    """
    def __init__(self, request):
        self.request = request
        self.model_collections = self.request.registry._model_collections

    def _set_object_self(self, obj):
        """ Add '_self' key value to :obj: dict. """
        from nefertari.elasticsearch import ES
        location = self.request.path_url
        route_kwargs = {}

        """ Check for parents """
        if self.request.matchdict:
            route_kwargs.update(self.request.matchdict)
        try:
            type_, obj_pk = obj['_type'], obj['_pk']
        except KeyError:
            return
        resource = (self.model_collections.get(type_) or
                    self.model_collections.get(ES.src2type(type_)))
        if resource is not None:
            route_kwargs.update({resource.id_name: obj_pk})
            location = self.request.route_url(
                resource.uid, **route_kwargs)
        obj.setdefault('_self', location)

    def __call__(self, **kwargs):
        result = kwargs['result']

        if 'data' not in result:
            self._set_object_self(result)
            return result

        try:
            for each in result['data']:
                try:
                    self._set_object_self(each)
                except TypeError:
                    pass
        finally:
            return result


class add_confirmation_url(object):
    """ Add confirmation url to confirm some action.

    Confirmation url is generated using `self.request.url`, `s__confirmation`
    query param and a method name in `_m` param.
    """
    def __init__(self, request):
        self.request = request

    def __call__(self, **kwargs):
        result = kwargs['result']
        q_or_a = '&' if self.request.params else '?'

        if isinstance(result, six.integer_types):
            return result

        return dict(
            method=self.request.method,
            count=engine.BaseDocument.count(result),
            confirmation_url=self.request.url+'%s__confirmation&_m=%s' % (
                q_or_a, self.request.method))


class set_total(object):
    def __init__(self, request, total):
        self.request = request
        self.total = total

    def __call__(self, **kwargs):
        result = kwargs['result']
        try:
            result._nefertari_meta['total'] = min(
                self.total, result._nefertari_meta['total'])
        except (AttributeError, TypeError):
            pass
        return result


class set_public_count(object):
    """ Wrapper that makes sure `_count` query returns number that is
    in `public_max_limit` bounds.
    """
    def __init__(self, request, public_max):
        """
        :param request: Pyramid Request instance.
        :param public_max: Value of `public_max_limit` setting.
        """
        self.request = request
        self.public_max = public_max

    def __call__(self, **kwargs):
        count = kwargs['result']
        try:
            count = min(self.public_max, count)
        except (KeyError, TypeError):
            pass
        return count


def set_public_limits(view):
    public_max = int(view.request.registry.settings.get(
        'public_max_limit', 100))

    try:
        _limit = int(view._query_params.get('_limit', 20))
        _page = int(view._query_params.get('_page', 0))
        _start = int(view._query_params.get('_start', 0))

        total_wrapper = set_total(view.request, total=public_max)
        view.add_after_call('index', total_wrapper, pos=0)

        if '_count' in view._query_params:
            count_wrapper = set_public_count(
                view.request, public_max=public_max)
            view.add_after_call('index', count_wrapper, pos=0)

    except ValueError:
        from nefertari.json_httpexceptions import JHTTPBadRequest
        raise JHTTPBadRequest("Bad _limit/_page param")

    _start = _start or _page * _limit
    if _start + _limit > public_max:
        view._query_params['_limit'] = max((public_max - _start), 0)
