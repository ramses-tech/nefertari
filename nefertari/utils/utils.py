import os
import logging
from contextlib import contextmanager
import json

from pyramid.config import Configurator

from nefertari.renderers import _JSONEncoder


log = logging.getLogger(__name__)


def json_dumps(body, encoder=None):
    if encoder is None:
        encoder = _JSONEncoder
    return json.dumps(body, cls=encoder)


def split_strip(_str, on=','):
    lst = _str if isinstance(_str, list) else _str.split(on)
    return filter(bool, [e.strip() for e in lst])


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
            if isinstance(each, basestring) and each.find(',') != -1:
                _new.extend(split_strip(each))
            else:
                _new.append(each)

    elif isinstance(param, basestring) and param.find(',') != -1:
        _new = split_strip(param)

    return _new


def process_fields(_fields):
    fields_only = []
    fields_exclude = []

    if isinstance(_fields, basestring):
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
    return (not hasattr(arg, 'strip') and
            hasattr(arg, '__getitem__') or
            hasattr(arg, '__iter__'))
