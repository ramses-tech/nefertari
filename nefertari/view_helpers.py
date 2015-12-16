class OptionsViewMixin(object):
    """ Mixin that implements default handling of OPTIONS requests.

    Is used with nefertari.view.BaseView. Relies on last view variables
    and methods.

    Attributes:
        :_item_actions: Map of item routes action names to tuple of HTTP
            methods they handle
        :_collection_actions: Map of collection routes action names to
            tuple of HTTP methods they handle
    """
    _item_actions = {
        'show':         ('GET', 'HEAD'),
        'replace':      ('PUT',),
        'update':       ('PATCH',),
        'delete':       ('DELETE',),
    }
    _collection_actions = {
        'index':        ('GET', 'HEAD'),
        'create':       ('POST',),
        'update_many':  ('PUT', 'PATCH'),
        'delete_many':  ('DELETE',),
    }

    def _set_options_headers(self, methods):
        """ Set proper headers.

        Sets following headers:
            Allow
            Access-Control-Allow-Methods
            Access-Control-Allow-Headers

        Arguments:
            :methods: Sequence of HTTP method names that are value for
                requested URI
        """
        request = self.request
        response = request.response

        response.headers['Allow'] = ', '.join(sorted(methods))

        if 'Access-Control-Request-Method' in request.headers:
            response.headers['Access-Control-Allow-Methods'] = \
                ', '.join(sorted(methods))

        if 'Access-Control-Request-Headers' in request.headers:
            response.headers['Access-Control-Allow-Headers'] = \
                'origin, x-requested-with, content-type'

        return response

    def _get_handled_methods(self, actions_map):
        """ Get names of HTTP methods that can be used at requested URI.

        Arguments:
            :actions_map: Map of actions. Must have the same structure as
                self._item_actions and self._collection_actions
        """
        methods = ('OPTIONS',)

        defined_actions = []
        for action_name in actions_map.keys():
            view_method = getattr(self, action_name, None)
            method_exists = view_method is not None
            method_defined = view_method != self.not_allowed_action
            if method_exists and method_defined:
                defined_actions.append(action_name)

        for action in defined_actions:
            methods += actions_map[action]

        return methods

    def item_options(self, **kwargs):
        """ Handle collection OPTIONS request.

        Singular route requests are handled a bit differently because
        singular views may handle POST requests despite being registered
        as item routes.
        """
        actions = self._item_actions.copy()
        if self._resource.is_singular:
            actions['create'] = ('POST',)
        methods = self._get_handled_methods(actions)
        return self._set_options_headers(methods)

    def collection_options(self, **kwargs):
        """ Handle collection item OPTIONS request. """
        methods = self._get_handled_methods(self._collection_actions)
        return self._set_options_headers(methods)
