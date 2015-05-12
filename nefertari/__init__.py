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

    log.info("%s %s" % (APP_NAME, __version__))
    config.add_directive('get_root_resource', get_root_resource)
    config.add_renderer('json', JsonRendererFactory)
    config.add_renderer('nefertari_json', NefertariJsonRendererFactory)

    if not hasattr(config.registry, '_root_resources'):
        config.registry._root_resources = {}
    if not hasattr(config.registry, '_resources_map'):
        config.registry._resources_map = {}

    config.add_request_method(get_resource_map, 'resource_map', reify=True)

    config.add_tween('nefertari.tweens.cache_control')

    config.add_route('options', '/*path', request_method='OPTIONS')
    config.add_view(view='nefertari.utility_views.OptionsView',
                    route_name='options')
