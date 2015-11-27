import logging

from pkg_resources import get_distribution

APP_NAME = __package__.split('.')[0]
_DIST = get_distribution(APP_NAME)
PROJECTDIR = _DIST.location
__version__ = _DIST.version

log = logging.getLogger(__name__)

RESERVED_PARAMS = [
    '_start',
    '_limit',
    '_page',
    '_fields',
    '_count',
    '_sort',
    '_search_fields',
    '_refresh_index',
]


def includeme(config):
    from nefertari.resource import get_root_resource, get_resource_map
    from nefertari.renderers import (
        JsonRendererFactory, NefertariJsonRendererFactory)
    from nefertari.utils import dictset
    from nefertari.events import (
        ModelClassIs, FieldIsChanged, subscribe_to_events,
        add_field_processors)

    log.info("%s %s" % (APP_NAME, __version__))
    config.add_directive('get_root_resource', get_root_resource)
    config.add_directive('subscribe_to_events', subscribe_to_events)
    config.add_directive('add_field_processors', add_field_processors)
    config.add_renderer('json', JsonRendererFactory)
    config.add_renderer('nefertari_json', NefertariJsonRendererFactory)

    if not hasattr(config.registry, '_root_resources'):
        config.registry._root_resources = {}
    if not hasattr(config.registry, '_resources_map'):
        config.registry._resources_map = {}
    # Map of {ModelName: model_collection_resource}
    if not hasattr(config.registry, '_model_collections'):
        config.registry._model_collections = {}

    config.add_request_method(get_resource_map, 'resource_map', reify=True)

    config.add_tween('nefertari.tweens.cache_control')

    config.add_subscriber_predicate('model', ModelClassIs)
    config.add_subscriber_predicate('field', FieldIsChanged)

    Settings = dictset(config.registry.settings)
    root = config.get_root_resource()
    root.auth = Settings.asbool('auth')
