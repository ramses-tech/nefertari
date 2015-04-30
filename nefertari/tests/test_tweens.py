import pytest
from mock import Mock, patch

from nefertari import tweens


def mock_timer():
    mock_timer.time = 0
    def time_func():
        mock_timer.time += 1
        return mock_timer.time
    return time_func


class TestTweens(object):

    @patch('nefertari.tweens.time')
    @patch('nefertari.tweens.log')
    def test_request_timing(self, mock_log, mock_time):
        mock_time.time = mock_timer()
        request = Mock(method='GET', url='http://example.com')
        registry = Mock()
        registry.settings = {'request_timing.slow_request_threshold': 1000}
        handler = lambda request: request
        timing = tweens.request_timing(handler, registry)
        timing(request)
        mock_log.debug.assert_called_once_with(
            'GET (http://example.com) request took 1 seconds')
        assert not mock_log.warning.called

    @patch('nefertari.tweens.time')
    @patch('nefertari.tweens.log')
    def test_request_timing_slow_request(self, mock_log, mock_time):
        mock_time.time = mock_timer()
        request = Mock(method='GET', url='http://example.com')
        registry = Mock()
        registry.settings = {'request_timing.slow_request_threshold': 0}
        handler = lambda request: request
        timing = tweens.request_timing(handler, registry)
        timing(request)
        mock_log.warning.assert_called_once_with(
            'GET (http://example.com) request took 1 seconds')
        assert not mock_log.debug.called

    def test_post_tunneling_get_param(self):
        request = Mock(
            GET={'_method': 'PUT'}, POST={}, headers={},
            method='POST')
        post_tunneling = tweens.post_tunneling(lambda x: x, None)
        post_tunneling(request)
        assert request.GET == {}
        assert request.POST == {}
        assert request.headers == {}
        assert request.method == 'PUT'

    def test_post_tunneling_post_param(self):
        request = Mock(
            GET={}, POST={'_method': 'PATCH'}, headers={},
            method='POST')
        post_tunneling = tweens.post_tunneling(lambda x: x, None)
        post_tunneling(request)
        assert request.GET == {}
        assert request.POST == {}
        assert request.headers == {}
        assert request.method == 'PATCH'

    def test_post_tunneling_header(self):
        request = Mock(
            GET={}, POST={}, method='POST',
            headers={'X-HTTP-Method-Override': 'DELETE'})
        post_tunneling = tweens.post_tunneling(lambda x: x, None)
        post_tunneling(request)
        assert request.GET == {}
        assert request.POST == {}
        assert request.headers == {}
        assert request.method == 'DELETE'

    def test_post_tunneling_not_allowed_method(self):
        request = Mock(
            GET={}, POST={}, method='POST',
            headers={'X-HTTP-Method-Override': 'GET'})
        post_tunneling = tweens.post_tunneling(lambda x: x, None)
        post_tunneling(request)
        assert request.GET == {}
        assert request.POST == {}
        assert request.headers == {'X-HTTP-Method-Override': 'GET'}
        assert request.method == 'POST'

    def test_get_tunneling(self):
        class GET(dict):
            def mixed(self):
                return self

        request = Mock(GET=GET({'_m': 'POST', 'foo': 'bar'}), method='GET')
        get_tunneling = tweens.get_tunneling(lambda x: x, None)
        get_tunneling(request)
        assert request.GET == {"foo": "bar"}
        assert request.method == 'POST'
        assert request.content_type == 'application/json'
        assert request.body == '{"foo": "bar"}'

    def test_get_tunneling_not_allowed_method(self):
        class GET(dict):
            def mixed(self):
                return self

        request = Mock(
            GET=GET({'_m': 'DELETE', 'foo': 'bar'}), method='GET',
            body=None, content_type=None)
        get_tunneling = tweens.get_tunneling(lambda x: x, None)
        get_tunneling(request)
        assert request.GET == {"foo": "bar"}
        assert request.method == 'DELETE'
        assert request.content_type is None
        assert request.body is None
