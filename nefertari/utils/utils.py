import os
import logging
import json
from contextlib import contextmanager

import six
from pyramid.config import Configurator


log = logging.getLogger(__name__)


def get_json_encoder():
    try:
        from nefertari import engine
        return engine.JSONEncoder
    except AttributeError:
        from nefertari.renderers import _JSONEncoder
        return _JSONEncoder


def json_dumps(body, encoder=None):
    if encoder is None:
        encoder = get_json_encoder()
    return json.dumps(body, cls=encoder)


def split_strip(_str, on=','):
    lst = _str if isinstance(_str, list) else _str.split(on)
    return list(filter(bool, [e.strip() for e in lst]))


def process_limit(start, page, limit):
    try:
        limit = int(limit)

        if start is not None and page is not None:
            raise ValueError('Can not specify _start and _page at the '
                             'same time')

        if start is not None:
            start = int(start)
        elif page is not None:
            start = int(page)*limit
        else:
            start = 0

        if limit < 0 or start < 0:
            raise ValueError('_limit/_page or _limit/_start can not be < 0')

    except (ValueError, TypeError) as e:
        raise ValueError(e)

    return start, limit


def extend_list(param):
    _new = []
    if isinstance(param, (list, set)):
        for each in param:
            if isinstance(each, six.string_types) and each.find(',') != -1:
                _new.extend(split_strip(each))
            else:
                _new.append(each)

    elif isinstance(param, six.string_types) and param.find(',') != -1:
        _new = split_strip(param)

    return _new


def process_fields(_fields):
    fields_only = []
    fields_exclude = []

    if isinstance(_fields, six.string_types):
        _fields = split_strip(_fields)

    for field in extend_list(_fields):
        field = field.strip()
        if not field:
            continue
        if field[0] == "-":
            fields_exclude.append(field[1:])
        else:
            fields_only.append(field)
    return fields_only, fields_exclude


def snake2camel(text):
    "turn the snake case to camel case: snake_camel -> SnakeCamel"
    return ''.join([a.title() for a in text.split("_")])


def maybe_dotted(module, throw=True):
    """ If ``module`` is a dotted string pointing to the module,
    imports and returns the module object.
    """
    try:
        return Configurator().maybe_dotted(module)
    except ImportError as e:
        err = '%s not found. %s' % (module, e)
        if throw:
            raise ImportError(err)
        else:
            log.error(err)
            return None


@contextmanager
def chdir(path):
    old_dir = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(old_dir)


def isnumeric(value):
    """Return True if `value` can be converted to a float."""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def issequence(arg):
    """Return True if `arg` acts as a list and does not look like a string."""
    string_behaviour = (
        isinstance(arg, six.string_types) or
        isinstance(arg, six.text_type))
    list_behaviour = hasattr(arg, '__getitem__') or hasattr(arg, '__iter__')
    return not string_behaviour and list_behaviour


def merge_dicts(a, b, path=None):
    """ Merge dict :b: into dict :a:

    Code snippet from http://stackoverflow.com/a/7205107
    """
    if path is None:
        path = []

    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge_dicts(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                raise Exception(
                    'Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


def str2dict(dotted_str, value=None, separator='.'):
    """ Convert dotted string to dict splitting by :separator: """
    dict_ = {}
    parts = dotted_str.split(separator)
    d, prev = dict_, None
    for part in parts:
        prev = d
        d = d.setdefault(part, {})
    else:
        if value is not None:
            prev[part] = value
    return dict_


def validate_data_privacy(request, data, wrapper_kw=None):
    """ Validate :data: contains only data allowed by privacy settings.

    :param request: Pyramid Request instance
    :param data: Dict containing request/response data which should be
        validated
    """
    from nefertari import wrappers
    if wrapper_kw is None:
        wrapper_kw = {}

    wrapper = wrappers.apply_privacy(request)
    allowed_fields = wrapper(result=data, **wrapper_kw).keys()
    data = data.copy()
    data.pop('_type', None)
    not_allowed_fields = set(data.keys()) - set(allowed_fields)

    if not_allowed_fields:
        raise wrappers.ValidationError(', '.join(not_allowed_fields))


def drop_reserved_params(params):
    """ Drops reserved params """
    from nefertari import RESERVED_PARAMS
    params = params.copy()
    for reserved_param in RESERVED_PARAMS:
        if reserved_param in params:
            params.pop(reserved_param)
    return params


def is_document(data):
    """ Determine whether :data: is a valid document.

    To be considered valid, data must:
        * Be an instance of dict
        * Have '_type' key in it
    """
    return isinstance(data, dict) and '_type' in data
