import datetime
import decimal
import logging

import elasticsearch

from nefertari.renderers import _JSONEncoder

log = logging.getLogger(__name__)


class MultiEngineMeta(type):
    def __new__(cls, name, bases, attrs):
        new_class = super(MultiEngineMeta, cls).__new__(
            cls, name, bases, attrs)
        return new_class


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
