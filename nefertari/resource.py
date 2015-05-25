import logging
from nefertari.utils import snake2camel, maybe_dotted

log = logging.getLogger(__name__)


ACTIONS = ['index', 'show', 'create', 'update',
           'delete', 'update_many', 'delete_many']
DEFAULT_ID_NAME = 'id'


def get_root_resource(config):
    "Returns the root resource."
    return config.registry._root_resources.setdefault(
        config.package_name,
        Resource(config))


def get_resource_map(request):
    return request.registry._resources_map


def add_resource_routes(config, view, member_name, collection_name, **kwargs):
    """
    ``view`` is a dotted name of (or direct reference to) a
    Python view class,
    e.g. ``'my.package.views.MyView'``.

    ``member_name`` should be the appropriate singular version of the resource
    given your locale and used with members of the collection.

    ``collection_name`` will be used to refer to the resource collection
    methods and should be a plural version of the member_name argument.

    All keyword arguments are optional.

    ``path_prefix``
        Prepends the URL path for the Route with the path_prefix
        given. This is most useful for cases where you want to mix
        resources or relations between resources.

    ``name_prefix``
        Prepends the route names that are generated with the
        name_prefix given. Combined with the path_prefix option,
        it's easy to generate route names and paths that represent
        resources that are in relations.

        Example::

            config.add_resource_routes(
                'myproject.views:CategoryView', 'message', 'messages',
                path_prefix='/category/{category_id}',
                name_prefix="category_")

            # GET /category/7/messages/1
            # has named route "category_message"

    """

    view = maybe_dotted(view)
    path_prefix = kwargs.pop('path_prefix', '')
    name_prefix = kwargs.pop('name_prefix', '')

    if config.route_prefix:
        name_prefix = "%s_%s" % (config.route_prefix, name_prefix)

    if collection_name:
        id_name = '/{%s}' % (kwargs.pop('id_name', None) or DEFAULT_ID_NAME)
    else:
        id_name = ''

    path = path_prefix.strip('/') + '/' + (collection_name or member_name)

    _factory = kwargs.pop('factory', None)
    # If factory is not set, than auth should be False
    _auth = kwargs.pop('auth', None) and _factory
    _traverse = (kwargs.pop('traverse', None) or id_name) if _factory else None

    action_route = {}
    added_routes = {}

    def add_route_and_view(config, action, route_name, path, request_method,
                           **route_kwargs):
        if route_name not in added_routes:
            config.add_route(
                route_name, path, factory=_factory,
                request_method=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
                **route_kwargs)
            added_routes[route_name] = path

        action_route[action] = route_name

        config.add_view(view=view, attr=action, route_name=route_name,
                        request_method=request_method,
                        permission=action if _auth else None,
                        **kwargs)
        config.commit()

    if collection_name:
        add_route_and_view(
            config, 'index', name_prefix + collection_name, path,
            'GET')

    add_route_and_view(
        config, 'show', name_prefix + member_name, path + id_name,
        'GET', traverse=_traverse)

    add_route_and_view(
        config, 'replace', name_prefix + member_name, path + id_name,
        'PUT', traverse=_traverse)

    add_route_and_view(
        config, 'update', name_prefix + member_name, path + id_name,
        'PATCH', traverse=_traverse)

    add_route_and_view(
        config, 'create', name_prefix + (collection_name or member_name), path,
        'POST')

    add_route_and_view(
        config, 'delete', name_prefix + member_name, path + id_name,
        'DELETE', traverse=_traverse)

    if collection_name:
        add_route_and_view(
            config, 'update_many',
            name_prefix + (collection_name or member_name),
            path, 'PUT', traverse=_traverse)

        add_route_and_view(
            config, 'update_many',
            name_prefix + (collection_name or member_name),
            path, 'PATCH', traverse=_traverse)

        add_route_and_view(
            config, 'delete_many',
            name_prefix + (collection_name or member_name),
            path, 'DELETE', traverse=_traverse)

    return action_route


def get_default_view_path(resource):
    "Returns the dotted path to the default view class."

    parts = [a.member_name for a in resource.ancestors] +\
            [resource.collection_name or resource.member_name]

    if resource.prefix:
        parts.insert(-1, resource.prefix)

    view_file = '%s' % '_'.join(parts)
    view = '%s:%sView' % (view_file, snake2camel(view_file))

    return '%s.views.%s' % (resource.config.package_name, view)


class Resource(object):

    """Class providing the core functionality.

    ::

        m = Resource(config)
        pa = m.add('parent', 'parents')
        pa.add('child', 'children')
    """

    def __init__(self, config, member_name='', collection_name='',
                 parent=None, uid='', children=None, id_name='', prefix='',
                 auth=False, http_cache=0, default_factory=None):

        self.__dict__.update(locals())
        self.children = children or []
        self._ancestors = []

    def __repr__(self):
        return "%s(uid='%s')" % (self.__class__.__name__, self.uid)

    def get_ancestors(self):
        "Returns the list of ancestor resources."

        if self._ancestors:
            return self._ancestors

        if not self.parent:
            return []

        obj = self.resource_map.get(self.parent.uid)

        while obj and obj.member_name:
            self._ancestors.append(obj)
            obj = obj.parent

        self._ancestors.reverse()
        return self._ancestors

    ancestors = property(get_ancestors)
    resource_map = property(lambda self: self.config.registry._resources_map)
    is_root = property(lambda self: not self.member_name)
    is_singular = property(
        lambda self: not self.is_root and not self.collection_name)

    def add(self, member_name, collection_name='', parent=None, uid='',
            **kwargs):
        """
        :param member_name: singular name of the resource. It should be the
            appropriate singular version of the resource given your locale
            and used with members of the collection.

        :param collection_name: plural name of the resource. It will be used
            to refer to the resource collection methods and should be a
            plural version of the ``member_name`` argument.
            Note: if collection_name is empty, it means resource is singular

        :param parent: parent resource name or object.

        :param uid: unique name for the resource

        :param kwargs:
            view: custom view to overwrite the default one.
            the rest of the keyward arguments are passed to
            add_resource_routes call.

        :return: ResourceMap object
        """
        # self is the parent resource on which this method is called.
        parent = (self.resource_map.get(parent) if type(parent)
                  is str else parent or self)

        prefix = kwargs.pop('prefix', '')

        uid = (uid or
               ':'.join(filter(bool, [parent.uid, prefix, member_name])))

        if uid in self.resource_map:
            raise ValueError('%s already exists in resource map' % uid)

        new_resource = Resource(self.config, member_name=member_name,
                                collection_name=collection_name,
                                parent=parent, uid=uid,
                                id_name=kwargs.get('id_name', ''),
                                prefix=prefix)

        view = maybe_dotted(
            kwargs.pop('view', None) or get_default_view_path(new_resource))

        for name, val in kwargs.pop('view_args', {}).items():
            setattr(view, name, val)

        root_resource = self.config.get_root_resource()

        view.root_resource = root_resource
        new_resource.view = view
        path_segs = []
        kwargs['path_prefix'] = ''

        for res in new_resource.ancestors:
            if not res.is_singular:
                if res.id_name:
                    id_full = res.id_name
                else:
                    id_full = "%s_%s" % (res.member_name, DEFAULT_ID_NAME)

                path_segs.append('%s/{%s}' % (res.collection_name, id_full))
            else:
                path_segs.append(res.member_name)

        if path_segs:
            kwargs['path_prefix'] = '/'.join(path_segs)

        if prefix:
            kwargs['path_prefix'] += '/' + prefix

        name_segs = [a.member_name for a in new_resource.ancestors]
        name_segs.insert(1, prefix)
        name_segs = filter(bool, name_segs)
        if name_segs:
            kwargs['name_prefix'] = '_'.join(name_segs) + ':'

        new_resource.renderer = kwargs.setdefault(
            'renderer', view._default_renderer)

        kwargs.setdefault('auth', root_resource.auth)
        kwargs.setdefault('factory', root_resource.default_factory)
        _factory = maybe_dotted(kwargs['factory'])

        kwargs['auth'] = kwargs.get('auth', root_resource.auth)

        kwargs['http_cache'] = kwargs.get(
            'http_cache', root_resource.http_cache)

        new_resource.action_route_map = add_resource_routes(
            self.config, view, member_name, collection_name,
            **kwargs)

        self.resource_map[uid] = new_resource
        # add all route names for this resource as keys in the dict,
        # so its easy to find it in the view.
        self.resource_map.update(dict.fromkeys(
            new_resource.action_route_map.values(),
            new_resource))

        parent.children.append(new_resource)
        view._resource = new_resource
        view._factory = _factory

        return new_resource

    def add_from_child(self, resource, **kwargs):
        """ Add a resource with its all children resources to the current
        resource.
        """

        new_resource = self.add(
            resource.member_name, resource.collection_name, **kwargs)
        for child in resource.children:
            new_resource.add_from_child(child, **kwargs)
