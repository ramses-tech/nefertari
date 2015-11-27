import six

from nefertari.utils import dictset, validate_data_privacy
from nefertari import wrappers
from nefertari.json_httpexceptions import JHTTPForbidden


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


class ESAggregator(object):
    """ Provides methods to perform Elasticsearch aggregations.

    Example of using ESAggregator:
        >> # Create an instance with view
        >> aggregator = ESAggregator(view)
        >> # Replace view.index with wrapped version
        >> view.index = aggregator.wrap(view.index)

    Attributes:
        :_aggregations_keys: Sequence of strings representing name(s) of the
            root key under which aggregations names are defined. Order of keys
            matters - first key found in request is popped and returned. May be
            overriden by defining it on view.

    Examples:
        If _aggregations_keys=('_aggregations',), then query string params
        should look like:
            _aggregations.min_price.min.field=price
    """
    _aggregations_keys = ('_aggregations', '_aggs')

    def __init__(self, view):
        self.view = view
        view_aggregations_keys = getattr(view, '_aggregations_keys', None)
        if view_aggregations_keys:
            self._aggregations_keys = view_aggregations_keys

    def wrap(self, func):
        """ Wrap :func: to perform aggregation on :func: call.

        Should be called with view instance methods.
        """
        @six.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return self.aggregate()
            except KeyError:
                return func(*args, **kwargs)
        return wrapper

    def pop_aggregations_params(self):
        """ Pop and return aggregation params from query string params.

        Aggregation params are expected to be prefixed(nested under) by
        any of `self._aggregations_keys`.
        """
        from nefertari.view import BaseView
        self._query_params = BaseView.convert_dotted(self.view._query_params)

        for key in self._aggregations_keys:
            if key in self._query_params:
                return self._query_params.pop(key)
        else:
            raise KeyError('Missing aggregation params')

    def stub_wrappers(self):
        """ Remove default 'index' after call wrappers and add only
        those needed for aggregation results output.
        """
        self.view._after_calls['index'] = []

    @classmethod
    def get_aggregations_fields(cls, params):
        """ Recursively get values under the 'field' key.

        Is used to get names of fields on which aggregations should be
        performed.
        """
        fields = []
        for key, val in params.items():
            if isinstance(val, dict):
                fields += cls.get_aggregations_fields(val)
            if key == 'field':
                fields.append(val)
        return fields

    def check_aggregations_privacy(self, aggregations_params):
        """ Check per-field privacy rules in aggregations.

        Privacy is checked by making sure user has access to the fields
        used in aggregations.
        """
        fields = self.get_aggregations_fields(aggregations_params)
        fields_dict = dictset.fromkeys(fields)
        fields_dict['_type'] = self.view.Model.__name__

        try:
            validate_data_privacy(self.view.request, fields_dict)
        except wrappers.ValidationError as ex:
            raise JHTTPForbidden(
                'Not enough permissions to aggregate on '
                'fields: {}'.format(ex))

    def aggregate(self):
        """ Perform aggregation and return response. """
        from nefertari.elasticsearch import ES
        aggregations_params = self.pop_aggregations_params()
        if self.view._auth_enabled:
            self.check_aggregations_privacy(aggregations_params)
        self.stub_wrappers()

        return ES(self.view.Model.__name__).aggregate(
            _aggregations_params=aggregations_params,
            **self._query_params)
