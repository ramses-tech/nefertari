import pytest
from mock import Mock, patch

from nefertari.view import BaseView
from nefertari.utils import dictset
from nefertari.view_helpers import ESAggregator


class DemoView(BaseView):
    """ BaseView inherits from OptionsViewMixin """
    def create(self):
        pass

    def index(self, **kwargs):
        pass

    def update(self):
        pass

    def delete(self):
        pass


class TestOptionsViewMixin(object):

    def _demo_view(self):
        return DemoView(**{
            'request': Mock(
                content_type='application/json',
                json={}, method='POST', accept=[''],
                headers={}, response=Mock(headers={})),
            'context': {'foo': 'bar'},
            '_query_params': {'foo': 'bar'},
            '_json_params': {'foo': 'bar'},
        })

    def test_set_options_headers(self):
        view = self._demo_view()
        view.request.headers = {
            'Access-Control-Request-Method': '',
            'Access-Control-Request-Headers': '',
        }
        view._set_options_headers(['GET', 'POST'])
        assert view.request.response.headers == {
            'Access-Control-Allow-Headers': 'origin, x-requested-with, content-type',
            'Access-Control-Allow-Methods': 'GET, POST',
            'Allow': 'GET, POST',
        }

    def test_get_handled_methods(self):
        view = self._demo_view()
        methods = view._get_handled_methods(view._item_actions)
        assert sorted(methods) == sorted(['DELETE', 'OPTIONS', 'PATCH'])
        methods = view._get_handled_methods(view._collection_actions)
        assert sorted(methods) == sorted([
            'GET', 'HEAD', 'OPTIONS', 'POST'])

    def test_item_options_singular(self):
        view = self._demo_view()
        expected_actions = view._item_actions.copy()
        expected_actions['create'] = ('POST',)
        view._get_handled_methods = Mock(return_value=['GET', 'POST'])
        view._set_options_headers = Mock(return_value=1)
        view._resource = Mock(is_singular=True)
        assert view.item_options() == 1
        view._get_handled_methods.assert_called_once_with(
            expected_actions)
        view._set_options_headers.assert_called_once_with(
            ['GET', 'POST'])

    def test_item_options_not_singular(self):
        view = self._demo_view()
        view._get_handled_methods = Mock(return_value=['GET', 'POST'])
        view._set_options_headers = Mock(return_value=1)
        view._resource = Mock(is_singular=False)
        assert view.item_options() == 1
        view._get_handled_methods.assert_called_once_with(
            view._item_actions)
        view._set_options_headers.assert_called_once_with(
            ['GET', 'POST'])

    def test_collection_options_not_singular(self):
        view = self._demo_view()
        view._get_handled_methods = Mock(return_value=['GET', 'POST'])
        view._set_options_headers = Mock(return_value=1)
        assert view.collection_options() == 1
        view._get_handled_methods.assert_called_once_with(
            view._collection_actions)
        view._set_options_headers.assert_called_once_with(
            ['GET', 'POST'])


class TestESAggregator(object):

    class DemoView(object):
        _aggregations_keys = ('test_aggregations',)
        _query_params = dictset()
        _json_params = dictset()

    def test_pop_aggregations_params_query_string(self):
        view = self.DemoView()
        view._query_params = {'test_aggregations.foo': 1, 'bar': 2}
        aggregator = ESAggregator(view)
        params = aggregator.pop_aggregations_params()
        assert params == {'foo': 1}
        assert aggregator._query_params == {'bar': 2}

    def test_pop_aggregations_params_keys_order(self):
        view = self.DemoView()
        view._query_params = {
            'test_aggregations.foo': 1,
            'foobar': 2,
        }
        aggregator = ESAggregator(view)
        aggregator._aggregations_keys = ('test_aggregations', 'foobar')
        params = aggregator.pop_aggregations_params()
        assert params == {'foo': 1}
        assert aggregator._query_params == {'foobar': 2}

    def test_pop_aggregations_params_mey_error(self):
        view = self.DemoView()
        aggregator = ESAggregator(view)
        with pytest.raises(KeyError) as ex:
            aggregator.pop_aggregations_params()
        assert 'Missing aggregation params' in str(ex.value)

    def test_stub_wrappers(self):
        view = self.DemoView()
        view._after_calls = {'index': [1, 2, 3], 'show': [1, 2]}
        aggregator = ESAggregator(view)
        aggregator.stub_wrappers()
        assert aggregator.view._after_calls == {'show': [1, 2], 'index': []}

    @patch('nefertari.elasticsearch.ES')
    def test_aggregate(self, mock_es):
        view = self.DemoView()
        view._auth_enabled = True
        view.Model = Mock(__name__='FooBar')
        aggregator = ESAggregator(view)
        aggregator.check_aggregations_privacy = Mock()
        aggregator.stub_wrappers = Mock()
        aggregator.pop_aggregations_params = Mock(return_value={'foo': 1})
        aggregator._query_params = {'q': '2', 'zoo': 3}
        aggregator.aggregate()
        aggregator.stub_wrappers.assert_called_once_with()
        aggregator.pop_aggregations_params.assert_called_once_with()
        aggregator.check_aggregations_privacy.assert_called_once_with(
            {'foo': 1})
        mock_es.assert_called_once_with('FooBar')
        mock_es().aggregate.assert_called_once_with(
            _aggregations_params={'foo': 1},
            _raw_terms='2',
            zoo=3)

    def test_get_aggregations_fields(self):
        params = {
            'min': {'field': 'foo'},
            'histogram': {'field': 'bar', 'interval': 10},
            'aggregations': {
                'my_agg': {
                    'max': {'field': 'baz'}
                }
            }
        }
        result = sorted(ESAggregator.get_aggregations_fields(params))
        assert result == sorted(['foo', 'bar', 'baz'])

    @patch('nefertari.view.wrappers.apply_privacy')
    def test_check_aggregations_privacy_all_allowed(self, mock_privacy):
        view = self.DemoView()
        view.request = 1
        view.Model = Mock(__name__='Zoo')
        aggregator = ESAggregator(view)
        aggregator.get_aggregations_fields = Mock(return_value=['foo', 'bar'])
        wrapper = Mock()
        mock_privacy.return_value = wrapper
        wrapper.return_value = {'foo': None, 'bar': None}
        try:
            aggregator.check_aggregations_privacy({'zoo': 2})
        except ValueError:
            raise Exception('Unexpected error')
        aggregator.get_aggregations_fields.assert_called_once_with({'zoo': 2})
        mock_privacy.assert_called_once_with(1)
        wrapper.assert_called_once_with(
            result={'_type': 'Zoo', 'foo': None, 'bar': None})

    @patch('nefertari.view.wrappers.apply_privacy')
    def test_check_aggregations_privacy_not_allowed(self, mock_privacy):
        view = self.DemoView()
        view.request = 1
        view.Model = Mock(__name__='Zoo')
        aggregator = ESAggregator(view)
        aggregator.get_aggregations_fields = Mock(return_value=['foo', 'bar'])
        wrapper = Mock()
        mock_privacy.return_value = wrapper
        wrapper.return_value = {'bar': None}
        with pytest.raises(ValueError) as ex:
            aggregator.check_aggregations_privacy({'zoo': 2})
        expected = 'Not enough permissions to aggregate on fields: foo'
        assert expected == str(ex.value)
        aggregator.get_aggregations_fields.assert_called_once_with({'zoo': 2})
        mock_privacy.assert_called_once_with(1)
        wrapper.assert_called_once_with(
            result={'_type': 'Zoo', 'foo': None, 'bar': None})

    def view_aggregations_keys_used(self):
        view = self.DemoView()
        view._aggregations_keys = ('foo',)
        assert ESAggregator(view)._aggregations_keys == ('foo',)
        view._aggregations_keys = None
        assert ESAggregator(view)._aggregations_keys == (
            '_aggregations', '_aggs')

    def test_wrap(self):
        view = self.DemoView()
        view.index = Mock()
        aggregator = ESAggregator(view)
        aggregator.aggregate = Mock(side_effect=KeyError)
        func = aggregator.wrap(view.index)
        func(1, 2)
        aggregator.aggregate.assert_called_once_with()
        view.index.assert_called_once_with(1, 2)
