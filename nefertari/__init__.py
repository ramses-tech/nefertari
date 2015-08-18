import logging

from pkg_resources import get_distribution

APP_NAME = __package__.split('.')[0]
_DIST = get_distribution(APP_NAME)
PROJECTDIR = _DIST.location
__version__ = _DIST.version

log = logging.getLogger(__name__)


def includeme(config):
    from nefertari.resource import get_root_resource, get_resource_map
    from nefertari.renderers import (
        JsonRendererFactory, NefertariJsonRendererFactory)
    from nefertari.utils import dictset

    log.info("%s %s" % (APP_NAME, __version__))
    config.add_directive('get_root_resource', get_root_resource)
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

    Settings = dictset(config.registry.settings)
    root = config.get_root_resource()
    root.auth = Settings.asbool('auth')
