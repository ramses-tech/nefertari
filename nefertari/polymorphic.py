"""
Module that defines all the objects required to handle polymorphic
collection read requests.

Only ES-based models that have collection view registered are handled
by this module.

Im particular:
    * PolymorphicACL: Dynamic factory class that generates ACL considering
        ACLs of all the collections requested.
    * PolymorphicESView: View that handles polymorphic collection read
        requests.

To use this module, simply include it in your `main()` after
Pyramid ACLAuthorizationPolicy is set up and nefertari is included.

By default this module is included by 'nefertari.elasticsearch' when
`elasticsearch.enable_polymorphic_query` setting is True.

After inclusion, PolymorphicESView view will be registered to handle GET
requests. To access polymorphic API endpoint, compose URL with names
used to access collection GET API endpoints.

E.g. If API had collection endpoints '/users' and '/stories', polymorphic
endpoint would be available at '/users,stories' and '/stories,users'.

Polymorphic endpoints support all the read functionality regular ES
endpoint supports: query, search, filter, sort, aggregation, etc.
"""
from pyramid.security import DENY_ALL, Allow, ALL_PERMISSIONS

from nefertari.view import BaseView
from nefertari.acl import CollectionACL
from nefertari.utils import dictset


def includeme(config):
    """ Connect view to route that catches all URIs like
    'something,something,...'
    """
    root = config.get_root_resource()
    root.add('nef_polymorphic', '{collections:.+,.+}',
             view=PolymorphicESView,
             factory=PolymorphicACL)


class PolymorphicHelperMixin(object):
    """ Helper mixin class that contains methods used by:
        * PolymorphicACL
        * PolymorphicESView
    """
    def get_collections(self):
        """ Get names of collections from request matchdict.

        :return: Names of collections
        :rtype: list of str
        """
        collections = self.request.matchdict['collections'].split('/')[0]
        collections = [coll.strip() for coll in collections.split(',')]
        return set(collections)

    def get_resources(self, collections):
        """ Get resources that correspond to values from :collections:.

        :param collections: Collection names for which resources should be
            gathered
        :type collections: list of str
        :return: Gathered resources
        :rtype: list of Resource instances
        """
        res_map = self.request.registry._model_collections
        resources = [res for res in res_map.values()
                     if res.collection_name in collections]
        resources = [res for res in resources if res]
        return set(resources)


class PolymorphicACL(PolymorphicHelperMixin, CollectionACL):
    """ ACL used by PolymorphicESView.

    Generates ACEs checking whether current request user has 'view'
    permissions in all of the requested collection views/contexts.
    """
    def __init__(self, request):
        """ Set ACL generated from collections affected. """
        super(PolymorphicACL, self).__init__(request)
        self.set_collections_acl()

    def _get_least_permissions_aces(self, resources):
        """ Get ACEs with the least permissions that fit all resources.

        To have access to polymorph on N collections, user MUST have
        access to all of them. If this is true, ACEs are returned, that
        allows 'view' permissions to current request principals.

        Otherwise None is returned thus blocking all permissions except
        those defined in `nefertari.acl.BaseACL`.

        :param resources:
        :type resources: list of Resource instances
        :return: Generated Pyramid ACEs or None
        :rtype: tuple or None
        """
        factories = [res.view._factory for res in resources]
        contexts = [factory(self.request) for factory in factories]
        for ctx in contexts:
            if not self.request.has_permission('view', ctx):
                return
        else:
            return [
                (Allow, principal, 'view')
                for principal in self.request.effective_principals
            ]

    def set_collections_acl(self):
        """ Calculate and set ACL valid for requested collections.

        DENY_ALL is added to ACL to make sure no access rules are
        inherited.
        """
        acl = [(Allow, 'g:admin', ALL_PERMISSIONS)]
        collections = self.get_collections()
        resources = self.get_resources(collections)
        aces = self._get_least_permissions_aces(resources)
        if aces is not None:
            for ace in aces:
                acl.append(ace)
        acl.append(DENY_ALL)
        self.__acl__ = tuple(acl)


class PolymorphicESView(PolymorphicHelperMixin, BaseView):
    """ Polymorphic ES collection read view.

    Has default implementation of 'index' view method that supports
    all the ES collection read actions(query, aggregation, etc.) across
    multiple collections of ES-based documents.

    To be displayed by polymorphic view, model must have collection view
    setup that serves instances of this model. Models that only have
    singular views setup are not served by polymorhic view.
    """
    def __init__(self, *args, **kwargs):
        """ Init view and set fake `self.Model` so its __name__ would
        contain names of all requested collections.
        """
        super(PolymorphicESView, self).__init__(*args, **kwargs)
        types = self.determine_types()
        self.Model = dictset({'__name__': ','.join(types)})

    def _run_init_actions(self):
        self.setup_default_wrappers()
        self.set_public_limits()

    def determine_types(self):
        """ Determine ES type names from request data.

        In particular `request.matchdict['collections']` is used to
        determine types names. Its value is comma-separated sequence
        of collection names under which views have been registered.
        """
        from nefertari.elasticsearch import ES
        collections = self.get_collections()
        resources = self.get_resources(collections)
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
