import six
from nefertari.utils.dictset import dictset
from nefertari.utils.utils import issequence


class DataProxy(object):
    def __init__(self, data={}):
        self._data = dictset(data)

    def to_dict(self, **kwargs):
        _dict = dictset()
        _keys = kwargs.pop('_keys', [])
        __depth = kwargs.pop('__depth', 10)

        data = dictset(self._data).subset(_keys) if _keys else self._data

        for attr, val in data.items():
            _dict[attr] = val
            if __depth:
                kw = kwargs.copy()
                kw['__nested'] = True
                kw['__depth'] = __depth - 1

                if hasattr(val, 'to_dict'):
                    _dict[attr] = val.to_dict(**kw)
                elif isinstance(val, list):
                    _dict[attr] = to_dicts(val, **kw)

        _dict['_type'] = self.__class__.__name__
        return _dict


def dict2obj(data):
    if not data:
        return data

    _type = str(data.get('_type'))
    top = type(_type, (DataProxy,), {})(data)

    for key, val in top._data.items():
        key = str(key)
        if isinstance(val, dict):
            setattr(top, key, dict2obj(val))
        elif isinstance(val, list):
            setattr(
                top, key,
                [dict2obj(sj) if isinstance(sj, dict) else sj for sj in val])
        else:
            setattr(top, key, val)

    return top


def to_objs(collection):
    _objs = []

    for each in collection:
        _objs.append(dict2obj(each))

    return _objs


def to_dicts(collection, key=None, **kw):
    _dicts = []
    try:
        for each in collection:
            try:
                each_dict = each.to_dict(**kw)
                if key:
                    each_dict = key(each_dict)
                _dicts.append(each_dict)
            except AttributeError:
                _dicts.append(each)
    except TypeError:
        return collection

    return _dicts


def obj2dict(obj, classkey=None):
    if isinstance(obj, dict):
        for k in obj.keys():
            obj[k] = obj2dict(obj[k], classkey)
        return obj
    elif issequence(obj):
        return [obj2dict(v, classkey) for v in obj]
    elif hasattr(obj, "__dict__"):
        data = dictset([
            (key, obj2dict(value, classkey))
            for key, value in obj.__dict__.items()
            if not six.callable(value) and not key.startswith('_')
        ])
        if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
        return data
    else:
        return obj
