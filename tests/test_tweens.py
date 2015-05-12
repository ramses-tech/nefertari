from mock import Mock, patch

from nefertari import tweens


def mock_timer():
    mock_timer.time = 0

    def time_func():
        mock_timer.time += 1
        return mock_timer.time
    return time_func


class DummyConfigurator(object):
    def __init__(self):
        self.subscribed = []

    def add_subscriber(self, wrapped, ifaces):
        self.subscribed.append((wrapped, ifaces))


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

    def test_cors_no_origins_no_creds(self):
        registry = Mock(settings={
            'cors.allow_origins': '',
            'cors.allow_credentials': None,
        })
        handler = lambda x: Mock(headerlist=[])
        request = Mock(
            headers={'Origin': '127.0.0.1:8080'},
            host_url='127.0.0.1:8080')
        response = tweens.cors(handler, registry)(request)
        assert response.headerlist == []

    def test_cors_disallow_creds(self):
        registry = Mock(settings={
            'cors.allow_origins': '',
            'cors.allow_credentials': False,
        })
        handler = lambda x: Mock(headerlist=[])
        request = Mock(
            headers={'Origin': '127.0.0.1:8080'},
            host_url='127.0.0.1:8080')
        response = tweens.cors(handler, registry)(request)
        assert response.headerlist == [
            ('Access-Control-Allow-Credentials', False)]

    def test_cors_allow_creds_and_origin(self):
        registry = Mock(settings={
            'cors.allow_origins': '127.0.0.1:8080,127.0.0.1:8090',
            'cors.allow_credentials': True,
        })
        handler = lambda x: Mock(headerlist=[])
        request = Mock(
            headers={'Origin': '127.0.0.1:8080'},
            host_url='127.0.0.1:8080')
        response = tweens.cors(handler, registry)(request)
        assert response.headerlist == [
            ('Access-Control-Allow-Origin', '127.0.0.1:8080'),
            ('Access-Control-Allow-Credentials', True)]

    def test_cors_wrong_origin(self):
        registry = Mock(settings={
            'cors.allow_origins': '127.0.0.1:8080,127.0.0.1:8090',
            'cors.allow_credentials': None,
        })
        handler = lambda x: Mock(headerlist=[])
        request = Mock(
            headers={'Origin': '127.0.0.1:8000'},
            host_url='127.0.0.1:8000')
        response = tweens.cors(handler, registry)(request)
        assert response.headerlist == []

    def test_cors_source_or_host_url(self):
        registry = Mock(settings={
            'cors.allow_origins': '127.0.0.1:8080,127.0.0.1:8090',
            'cors.allow_credentials': None,
        })
        handler = lambda x: Mock(headerlist=[])
        request = Mock(
            headers={'Origin': '127.0.0.1:8080'},
            host_url='')
        response = tweens.cors(handler, registry)(request)
        assert response.headerlist == [
            ('Access-Control-Allow-Origin', '127.0.0.1:8080')]

        request = Mock(
            headers={},
            host_url='127.0.0.1:8080')
        response = tweens.cors(handler, registry)(request)
        assert response.headerlist == [
            ('Access-Control-Allow-Origin', '127.0.0.1:8080')]

    def test_cors_allow_origins_star(self):
        registry = Mock(settings={
            'cors.allow_origins': '*',
            'cors.allow_credentials': True,
        })
        handler = lambda x: Mock(headerlist=[])
        cors = tweens.cors(handler, registry)
        assert cors is None

    def test_cache_control_header_not_set(self):
        handler = lambda x: Mock(headerlist=[('Cache-Control', '')])
        response = tweens.cache_control(handler, None)(None)
        assert not response.cache_expires.called

    def test_cache_control_header_set(self):
        handler = lambda x: Mock(headerlist=[])
        response = tweens.cache_control(handler, None)(None)
        response.cache_expires.assert_called_once_with(0)

    def test_ssl_url_scheme(self):
        request = Mock(
            scheme=None,
            environ={'HTTP_X_URL_SCHEME': 'Foo'}
        )
        tweens.ssl(lambda x: x, None)(request)
        assert request.environ['wsgi.url_scheme'] == 'foo'
        assert request.scheme == 'foo'

    def test_ssl_forwarded_proto(self):
        request = Mock(
            scheme=None,
            environ={'HTTP_X_FORWARDED_PROTO': 'Foo'}
        )
        tweens.ssl(lambda x: x, None)(request)
        assert request.environ['wsgi.url_scheme'] == 'foo'
        assert request.scheme == 'foo'

    def test_ssl_no_scheme(self):
        request = Mock(scheme=None, environ={})
        tweens.ssl(lambda x: x, None)(request)
        assert request.environ == {}
        assert request.scheme is None

    def test_enable_selfalias(self):
        from pyramid.events import ContextFound
        config = DummyConfigurator()
        assert config.subscribed == []
        tweens.enable_selfalias(config, 'foo')
        assert len(config.subscribed) == 1
        assert callable(config.subscribed[0][0])
        assert config.subscribed[0][1] is ContextFound

    def test_context_found_subscriber_alias_enabled(self):
        config = DummyConfigurator()
        tweens.enable_selfalias(config, 'foo')
        context_found_subscriber = config.subscribed[0][0]
        request = Mock(
            user=Mock(username='user12'),
            matchdict={'foo': 'self'})
        context_found_subscriber(Mock(request=request))
        assert request.matchdict['foo'] == 'user12'

    def test_context_found_subscriber_no_matchdict(self):
        config = DummyConfigurator()
        tweens.enable_selfalias(config, 'foo')
        context_found_subscriber = config.subscribed[0][0]
        request = Mock(
            user=Mock(username='user12'),
            matchdict=None)
        context_found_subscriber(Mock(request=request))
        assert request.matchdict is None

    def test_context_found_subscriber_not_self(self):
        config = DummyConfigurator()
        tweens.enable_selfalias(config, 'foo')
        context_found_subscriber = config.subscribed[0][0]
        request = Mock(
            user=Mock(username='user12'),
            matchdict={'foo': '1'})
        context_found_subscriber(Mock(request=request))
        assert request.matchdict['foo'] == '1'

    def test_context_found_subscriber_not_authenticated(self):
        config = DummyConfigurator()
        tweens.enable_selfalias(config, 'foo')
        context_found_subscriber = config.subscribed[0][0]
        request = Mock(
            user=None,
            matchdict={'foo': 'self'})
        context_found_subscriber(Mock(request=request))
        assert request.matchdict['foo'] == 'self'

    def test_context_found_subscriber_wrong_id_name(self):
        config = DummyConfigurator()
        tweens.enable_selfalias(config, 'foo')
        context_found_subscriber = config.subscribed[0][0]
        request = Mock(
            user=Mock(username='user12'),
            matchdict={'qoo': 'self'})
        context_found_subscriber(Mock(request=request))
        assert request.matchdict['qoo'] == 'self'
