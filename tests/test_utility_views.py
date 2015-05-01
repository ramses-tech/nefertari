import pytest
from mock import Mock

from nefertari import utility_views as uviews
from nefertari.json_httpexceptions import *


class TestOptionsView(object):
    header_str = 'HEAD, TRACE, GET, PATCH, PUT, POST, OPTIONS, DELETE'

    def test_call_methods_header(self):
        response = Mock(headers={})
        request = Mock(
            headers={'Access-Control-Request-Method': ''},
            response=response)
        resp = uviews.OptionsView(request=request)()
        assert resp is response
        assert response.headers == {
            'Allow': self.header_str,
            'Access-Control-Allow-Methods': self.header_str,
        }

    def test_call_headers_header(self):
        response = Mock(headers={})
        request = Mock(
            headers={'Access-Control-Request-Headers': ''},
            response=response)
        resp = uviews.OptionsView(request=request)()
        assert resp is response
        assert response.headers == {
            'Allow': self.header_str,
            'Access-Control-Allow-Headers': 'origin, x-requested-with, content-type',
        }

    def test_call_no_headers(self):
        response = Mock(headers={})
        request = Mock(
            headers={},
            response=response)
        resp = uviews.OptionsView(request=request)()
        assert resp is response
        assert response.headers == {
            'Allow': self.header_str,
        }


class DemoSettingsView(uviews.SettingsView):

    def __init__(self, *args, **kwargs):
        self.settings = {'status': 1}
        super(DemoSettingsView, self).__init__(*args, **kwargs)

    def _run_init_actions(self, *args, **kwargs):
        pass


class TestSettingsView(object):
    def _test_view(self):
        request = Mock(content_type='', method='', accept=[''], user=None)
        view = DemoSettingsView({}, request, _params={'foo': 'bar'})
        return view

    def test_index(self):
        view = self._test_view()
        assert view.index() == {'status': 1}

    def test_show(self):
        view = self._test_view()
        assert view.show('status') == 1

    def test_update(self):
        view = self._test_view()
        view._params['value'] = 2
        assert isinstance(view.update('status'), JHTTPOk)
        assert view.settings['status'] == 2

    def test_create(self):
        view = self._test_view()
        view._params['key'] = 'active'
        view._params['value'] = 4
        assert isinstance(view.create(), JHTTPCreated)
        assert view.settings == {'status': 1, 'active': 4}

    def test_delete(self):
        view = self._test_view()
        assert isinstance(view.delete('status'), JHTTPOk)
        assert view.settings == {}

    def test_delete_reset(self):
        view = self._test_view()
        view._params['reset'] = True
        view.request.registry.settings = {'status': 'ok'}
        assert isinstance(view.delete('status'), JHTTPOk)
        assert view.settings == {'status': 'ok'}

    def test_delete_many_confirm(self):
        view = self._test_view()
        view.needs_confirmation = lambda: True
        assert view.delete_many() == ['status']

    def test_delete_many_no_confirm(self):
        view = self._test_view()
        view.needs_confirmation = lambda: False
        view.settings = {'status': 3}
        assert isinstance(view.delete_many(), JHTTPOk)
        assert view.settings == {'status': 1}
