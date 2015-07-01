from pyramid.security import (
    DENY_ALL, Allow, principals_allowed_by_permission)

from nefertari.view import BaseView
from nefertari.acl import BaseACL
from nefertari.utils import dictset


def includeme(config):
    root = config.get_root_resource()
    root.add('nef_polymorphic', '{collections:.+,.+}',
             view=PolymorphicESView,
             factory=PolymorphicACL)


class PolymorphicHelperMixin(object):
    def _get_collections(self):
        """ Get names of collections from request. """
        collections = self.request.matchdict['collections'].split('/')[0]
        collections = [coll.strip() for coll in collections.split(',')]
        return set(collections)

    def _get_resources(self, collections):
        """ Get resources that correspond to names from :collections: """
        res_map = self.request.registry._resources_map
        resources = [res for res in res_map.values()
                     if res.collection_name in collections
                     or res.member_name in collections]
        resources = [res for res in resources if res]
        return set(resources)


class PolymorphicACL(PolymorphicHelperMixin, BaseACL):
    def __init__(self, request):
        super(PolymorphicACL, self).__init__(request)
        self.set_collections_acls()

    def _get_least_principals(self, resources):
        factories = [res.view._factory for res in resources]
        contexts = [factory(self.request) for factory in factories]
        # TODO: Get resource with least permissions
        # principals = principals_allowed_by_permission(ctx)


    def set_collections_acls(self):
        collections = self._get_collections()
        resources = self._get_resources(collections)
        principals = self._get_least_principals(resources)
        self.acl = (Allow, principals, 'index')
        self.acl = DENY_ALL




class PolymorphicESView(PolymorphicHelperMixin, BaseView):
    """ Polymorphic ES collection read view.

    Has default implementation of 'index' view method that supports
    all the ES collection read actions(query, aggregation, etc.) across
    multiple collections of ES-based documents.
    """
    def __init__(self, *args, **kwargs):
        """ Init view and set fake `self.Model` so its __name__ would
        contain names of all requested collections.
        """
        super(PolymorphicESView, self).__init__(*args, **kwargs)
        types = self.determine_types()
        self.Model = dictset({'__name__': ','.join(types)})

    def determine_types(self):
        """ Determine ES type names from request data.

        In particular `request.matchdict['collections']` is used to
        determine types names. Its value is comma-separated sequence
        of collection names under which views have been registered.
        """
        from nefertari.elasticsearch import ES
        collections = self._get_collections()
        resources = self._get_resources(collections)
        models = set([res.view.Model for res in resources])
        es_models = [mdl for mdl in models if mdl
                     and getattr(mdl, '_index_enabled', False)]
        types = [ES.src2type(mdl.__name__) for mdl in es_models]
        return types

    def index(self, collections):
        self._query_params.process_int_param('_limit', 20)
        return self.get_collection_es()
