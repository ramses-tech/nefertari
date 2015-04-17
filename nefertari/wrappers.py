import urllib
from hashlib import md5

import logging

log = logging.getLogger(__name__)


class ValidationError(Exception):
    pass


class ResourceNotFound(Exception):
    pass


def issequence(arg):
    """Return True if `arg` acts as a list and does not look like a string."""
    return (not hasattr(arg, 'strip') and
            hasattr(arg, '__getitem__') or
            hasattr(arg, '__iter__'))


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
    def __init__(self, request):
        self.request = request

    def __call__(self, **kwargs):
        '''converts objects in `result` into dicts'''

        result = kwargs['result']
        if isinstance(result, dict):
            return result

        _fields = kwargs.get('_fields', [])
        if hasattr(result, '_nefertari_meta'):
            _fields = result._nefertari_meta.get('fields', [])

        if hasattr(result, "to_dict"):
            return result.to_dict(_keys=_fields, request=self.request)

        elif issequence(result):
            #make sure its mutable, i.e list
            result = list(result)
            for ix, each in enumerate(result):
                result[ix] = obj2dict(self.request)(
                    _fields=_fields, result=each)

        return result


class wrap_in_dict(object):
    def __init__(self, request):
        self.request = request

    def __call__(self, **kwargs):
        '''if result is a list then wrap it in the dict'''
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
    def __init__(self, request):
        self.request = request

    def __call__(self, **kwargs):
        result = kwargs['result']

        try:
            result['count'] = len(result["data"])
            for each in result['data']:
                try:
                    each.setdefault('self', "%s/%s" % (
                        self.request.current_route_url(),
                        urllib.quote(str(each['id']))))
                except TypeError:
                    pass
        except (TypeError, KeyError):
            pass
        finally:
            return result


class add_confirmation_url(object):
    def __init__(self, request):
        self.request = request

    def __call__(self, **kwargs):
        from nefertari.engine import BaseDocument
        result = kwargs['result']
        q_or_a = '&' if self.request.params else '?'

        return dict(
            method=self.request.method,
            count=BaseDocument.count(result),
            confirmation_url=self.request.url+'%s__confirmation&_m=%s' % (
                q_or_a, self.request.method))


class add_etag(object):
    def __init__(self, request):
        self.request = request

    def __call__(self, **kwargs):
        result = kwargs['result']

        etag_src = ''

        def etag(data):
            return str(data.get('_version', '')) + str(data.get('id', ''))

        try:
            etag_src += etag(result)

            for each in result['data']:
                etag_src += etag(each)

        except (TypeError, KeyError) as e:
            pass

        finally:
            if etag_src:
                self.request.response.etag = md5(etag_src).hexdigest()
            return result


class set_total(object):
    def __init__(self, request, total):
        self.request = request
        self.total = total

    def __call__(self, **kwargs):
        result = kwargs['result']
        try:
            result._nefertari_meta['total'] = min(
                self.total, result._nefertari_meta['total'])
        except (AttributeError, TypeError) as e:
            pass
        return result


def set_public_limits(view):
    public_max = int(view.request.registry.settings.get(
        'public_max_limit', 100))

    try:
        _limit = int(view._params.get('_limit', 20))
        _page = int(view._params.get('_page', 0))
        _start = int(view._params.get('_start', 0))

        view.add_after_call('index', set_total(view.request, total=public_max),
                            pos=0)
    except ValueError:
        from nefertari.json_httpexceptions import JHTTPBadRequest
        raise JHTTPBadRequest("Bad _limit/_page param")

    _start = _start or _page*_limit
    if _start + _limit > public_max:
        view._params['_limit'] = max((public_max - _start), 0)
