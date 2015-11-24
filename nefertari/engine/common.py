import datetime
import decimal
import logging

import elasticsearch

from nefertari.renderers import _JSONEncoder
from nefertari import engine

log = logging.getLogger(__name__)


class MultiEngineMeta(type):
    def __init__(self, name, bases, attrs):
        super(MultiEngineMeta, self).__init__(name, bases, attrs)
        single_engine = engine.secondary is None
        already_generated = (
            getattr(self, '_primary', None) is not None or
            getattr(self, '_secondary', None) is not None)
        if self._is_abstract() or single_engine or already_generated:
            return

        replaced_bases = self._recreate_bases()
        fields = self._recreate_fields()
        new_attrs = {
            key: val for key, val in attrs.items()
            if key not in fields}
        new_attrs.update(fields)
        new_attrs['_primary'] = self

        metaclass = type(engine.secondary.BaseDocument)
        self._secondary = metaclass(
            name, tuple(replaced_bases), new_attrs)

    def _recreate_fields(self):
        fields = self._fields_map()
        fields_kw = {name: self.get_field_params(name)
                     for name in fields}

        recreated_fields = {}
        for fname, field in fields.items():
            field_kw = fields_kw[fname]
            field_cls = self._get_secondary(field.__class__)
            recreated_fields[fname] = field_cls(**field_kw)

        return recreated_fields

    def _recreate_bases(self):
        bases = list(self.__bases__)
        return [self._get_secondary(base) for base in bases]

    def _get_secondary(self, obj):
        try:
            type_name = obj.__name__
        except AttributeError:
            return obj
        if hasattr(engine.secondary, type_name):
            return getattr(engine.secondary, type_name)
        return obj


class MultiEngineDocMixin(object):
    @classmethod
    def get_collection(cls, **params):
        return super(MultiEngineDocMixin, cls).get_collection(
            **params)


class JSONEncoderMixin(object):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.strftime("%Y-%m-%dT%H:%M:%SZ")  # iso
        if isinstance(obj, datetime.time):
            return obj.strftime('%H:%M:%S')
        if isinstance(obj, datetime.timedelta):
            return obj.seconds
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super(JSONEncoderMixin, self).default(obj)


class JSONEncoder(JSONEncoderMixin, _JSONEncoder):
    """ JSON encoder class to be used in views to encode response. """
    def default(self, obj):
        if hasattr(obj, 'to_dict'):
            # If it got to this point, it means its a nested object.
            # Outter objects would have been handled with DataProxy.
            return obj.to_dict()
        return super(JSONEncoder, self).default(obj)


class ESJSONSerializer(JSONEncoderMixin,
                       elasticsearch.serializer.JSONSerializer):
    """ JSON encoder class used to serialize data before indexing
    to ES. """
    def default(self, obj):
        try:
            return super(ESJSONSerializer, self).default(obj)
        except:
            import traceback
            log.error(traceback.format_exc())
