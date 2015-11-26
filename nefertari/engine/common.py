import datetime
import decimal
import logging

import elasticsearch

from nefertari.renderers import _JSONEncoder
from nefertari import engine

log = logging.getLogger(__name__)


class MultiEngineMeta(type):
    """ Document metaclass to be used with multi-engine setup.

    Generates copy of model class but using classes from
    secondary engine.
    """
    def __init__(self, name, bases, attrs):
        super(MultiEngineMeta, self).__init__(name, bases, attrs)
        self._generate_secondary_model(name, attrs)

    def _generate_secondary_model(self, name, attrs):
        """ Generate secondary engine model.

        :param name: String name of model to be generated.
        :param attrs: Dict containing attrs used in creation of
            main class.
        """
        if not self._needs_generation():
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

    def _needs_generation(self):
        """ Determine whether secondary model class needs to be
        generated.

        :returns bool: True is secondary model class needs
            to be generated. False otherwise.
        """
        if self._is_abstract():
            return False
        if engine.secondary is None:
            return False
        already_generated = (
            getattr(self, '_primary', None) is not None or
            getattr(self, '_secondary', None) is not None)
        if already_generated:
            return False
        return True

    def _recreate_fields(self):
        """ Recreate primary model fields using secondary engine.

        :returns dict: Keys are field names, values are instances
            of secondary engine fields.
        """
        field_creators = self._get_fields_creators()
        fields_kw = {name: self.get_field_params(name)
                     for name in field_creators}

        recreated_fields = {}
        for fname, creator in field_creators.items():
            field_kw = fields_kw[fname] or {}
            field_kw = {key: self._get_secondary(val)
                        for key, val in field_kw.items()}
            secondary_creator = self._get_secondary(creator)
            recreated_fields[fname] = secondary_creator(**field_kw)

        return recreated_fields

    def _recreate_bases(self):
        """ Get secondary engine analogues of bases.

        E.g. if current class inherits from BaseDocument and secondary
        engine defines class BaseDocument, latter will replace prior.

        :returns list: of replaced base classes of primary model.
        """
        bases = list(self.__bases__)
        return [self._get_secondary(base) for base in bases]

    def _get_secondary(self, obj):
        """ Get ``obj`` analog from secondary engine.

        :returns: Analog of ``obj`` with the same name from secondary
            engine if exists. Returns ``obj`` otherwise.
        """
        try:
            type_name = obj.__name__
        except AttributeError:
            return obj
        if hasattr(engine.secondary, type_name):
            return getattr(engine.secondary, type_name)
        return obj


class MultiEngineDocMixin(object):
    """ Document/model base that implements logic required for
    multi-engine setup.
    """
    _primary = None
    _secondary = None

    @classmethod
    def get_collection(cls, _query_secondary=True, **params):
        if _query_secondary and cls._secondary is not None:
            return cls._secondary.get_collection(**params)
        return super(MultiEngineDocMixin, cls).get_collection(
            **params)


class JSONEncoderMixin(object):
    """ JSON encoder mixin that implements encoding of common
    data types.
    """
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
    to ES.
    """
    def default(self, obj):
        try:
            return super(ESJSONSerializer, self).default(obj)
        except:
            import traceback
            log.error(traceback.format_exc())
