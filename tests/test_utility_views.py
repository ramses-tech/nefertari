from mock import Mock

from nefertari.view import BaseView


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
