from pyramid.security import DENY_ALL, Allow, Denied

from nefertari.view import BaseView
from nefertari.acl import BaseACL
from nefertari.utils import dictset


def includeme(config):
    root = config.get_root_resource()
    root.add('nef_polymorphic', '{collections:.+,.+}',
             view=PolymorphicESView,
             factory=PolymorphicACL)


class PolymorphicHelperMixin(object):
    """ Helper mixin class that contains methods used by PolymorphicACL
    and PolymorphicESView.
    """
    def _get_collections(self):
        """ Get names of collections from request matchdict.

        :return: Names of collections
        :rtype: list of str
        """
        collections = self.request.matchdict['collections'].split('/')[0]
        collections = [coll.strip() for coll in collections.split(',')]
        return set(collections)

    def _get_resources(self, collections):
        """ Get resources that correspond to values from :collections:.

        :param collections: Collection names for which resources should be
            gathered
        :type collections: list of str
        :return: Gathered resources
        :rtype: list of Resource instances
        """
        res_map = self.request.registry._resources_map
        resources = [res for res in res_map.values()
                     if res.collection_name in collections
                     or res.member_name in collections]
        resources = [res for res in resources if res]
        return set(resources)


class PolymorphicACL(PolymorphicHelperMixin, BaseACL):
    """ ACL used by PolymorphicESView.

    Generates ACEs checking whether current request user has 'index'
    permissions in all of the requested collection views/contexts.
    """
    def __init__(self, request):
        """ Set ACL generated from collections affected. """
        super(PolymorphicACL, self).__init__(request)
        self.set_collections_acl()

    def _get_least_permissions_ace(self, resources):
        """ Get ACE with the least permissions that fits all resources.

        To have access to polymorph on N collections, user MUST have
        access to all of them. If this is true, ACE is returned, that
        allows 'index' permissions to current request principals.

        Otherwise None is returned thus blocking all permissions except
        those defined in `nefertari.acl.BaseACL`.

        :param resources:
        :type resources: list of Resource instances
        :return: Generated Pyramid ACE
        :rtype: tuple or None
        """
        factories = [res.view._factory for res in resources]
        contexts = [factory(self.request) for factory in factories]
        for ctx in contexts:
            has_perm = self.request.has_permission('index', ctx)
            if isinstance(has_perm, Denied):
                return
        else:
            return (Allow, self.request.effective_principals, 'index')

    def set_collections_acl(self):
        """ Calculate and set ACL valid for requested collections.

        DENY_ALL is added to ACL to make sure no access rules are
        inherited.
        """
        #
        # TODO: Test ACL is generated properly
        #
        collections = self._get_collections()
        resources = self._get_resources(collections)
        permissions = self._get_least_permissions_ace(resources)
        if permissions is not None:
            self.acl = permissions
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
        """ Handle collection GET request.

        Set default limit and call :self.get_collection_es: to query ES.
        """
        self._query_params.process_int_param('_limit', 20)
        return self.get_collection_es()
