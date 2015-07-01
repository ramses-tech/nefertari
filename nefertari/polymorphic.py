from nefertari.view import BaseView
from nefertari.acl import BaseACL
from nefertari.utils import dictset


def includeme(config):
    root = config.get_root_resource()
    root.add('nef_polymorphic', '{collections:.+,.+}',
             view=PolymorphicESView,
             factory=PolymorphicACL)


class PolymorphicACL(BaseACL):
    def __init__(self, request):
        super(PolymorphicACL, self).__init__(request)


class PolymorphicESView(BaseView):
    def __init__(self, *args, **kwargs):
        """ Init view and set fake `self.Model` so its __name__ would
        contain names of all requested collections.
        """
        super(PolymorphicESView, self).__init__(*args, **kwargs)
        types = self.determine_types()
        self.Model = dictset({'__name__': ','.join(types)})

    @staticmethod
    def _get_collections(request):
        """ Get names of collections from request. """
        collections = request.matchdict['collections'].split('/')[0]
        collections = [coll.strip() for coll in collections.split(',')]
        return set(collections)

    @staticmethod
    def _get_resources(request, collections):
        """ Get resources that correspond to names from :collections: """
        res_map = request.registry._resources_map
        resources = [res for res in res_map.values()
                     if res.collection_name in collections
                     or res.member_name in collections]
        resources = [res for res in resources if res]
        return resources

    def determine_types(self):
        from nefertari.elasticsearch import ES
        collections = PolymorphicESView._get_collections(self.request)
        resources = PolymorphicESView._get_resources(
            self.request, collections)
        models = set([res.view.Model for res in resources])
        es_models = [mdl for mdl in models if mdl
                     and getattr(mdl, '_index_enabled', False)]
        types = [ES.src2type(mdl.__name__) for mdl in es_models]
        return types

    def index(self, collections):
        self._query_params.process_int_param('_limit', 20)
        return self.get_collection_es()
