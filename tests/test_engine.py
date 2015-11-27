from mock import Mock, patch


class TestEngine(object):
    @patch('nefertari.engine.resolve')
    def test_includeme(self, mock_resolve):
        module = Mock()
        config = Mock()
        config.registry.settings = {'nefertari.engine': 'foo'}
        module.log = 1
        module.__testvar__ = 3
        module.another_var = 4
        module.includeme = 42
        module.__all__ = ['another_var', 'includeme']
        mock_resolve.return_value = module
        from nefertari import engine
        assert not hasattr(engine, 'log')
        assert not hasattr(engine, '__testvar__')
        assert not hasattr(engine, 'another_var')

        engine.includeme(config)

        config.include.assert_called_once_with('foo')
        mock_resolve.assert_called_with('foo')
        assert not hasattr(engine, 'log')
        assert not hasattr(engine, '__testvar__')
        assert hasattr(engine, 'another_var')
        assert engine.engines == (module, )

    @patch('nefertari.engine.resolve')
    def test_multiple_engines(self, mock_resolve):
        from nefertari import engine
        foo = Mock()
        bar = Mock()
        foo.__all__ = ['one', 'two']
        bar.__all__ = ['three', 'four']
        config = Mock()
        config.registry.settings = {'nefertari.engine': ['foo', 'bar']}
        mock_resolve.side_effect = lambda m: foo if m == 'foo' else bar
        engine.includeme(config)

        config.include.assert_any_call('foo')
        config.include.assert_any_call('bar')
        mock_resolve.assert_any_call('foo')
        mock_resolve.assert_any_call('bar')
        assert not hasattr(engine, 'three')
        assert not hasattr(engine, 'four')
        assert hasattr(engine, 'one')
        assert hasattr(engine, 'two')
        assert engine.engines == (foo, bar)
