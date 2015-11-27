import six
from nefertari.utils.dictset import dictset
from nefertari.utils.utils import issequence


class DataProxy(object):
    def __init__(self, data={}):
        self._data = dictset(data)

    def to_dict(self, **kwargs):
        _dict = dictset()
        _keys = kwargs.pop('_keys', [])
        _depth = kwargs.pop('_depth', 1)

        data = dictset(self._data).subset(_keys) if _keys else self._data

        for attr, val in data.items():
            _dict[attr] = val
            if _depth:
                kw = kwargs.copy()
                kw['_depth'] = _depth - 1

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


class FieldData(object):
    """ Keeps field data in a generic format.

    Is passed to field processors.
    """
    def __init__(self, name, new_value, params=None):
        """
        :param name: Name of field.
        :param new_value: New value of field.
        :param params: Dict containing DB field init params.
            E.g. min_length, required.
        """
        self.name = name
        self.new_value = new_value
        self.params = params

    def __repr__(self):
        return '<FieldData: {}>'.format(self.name)

    @classmethod
    def from_dict(cls, data, model):
        """ Generate map of `fieldName: clsInstance` from dict.

        :param data: Dict where keys are field names and values are
            new values of field.
        :param model: Model class to which fields from :data: belong.
        """
        model_provided = model is not None
        result = {}
        for name, new_value in data.items():
            kwargs = {
                'name': name,
                'new_value': new_value,
            }
            if model_provided:
                kwargs['params'] = model.get_field_params(name)
            result[name] = cls(**kwargs)
        return result
