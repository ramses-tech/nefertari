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
        mock_resolve.return_value = module
        from nefertari import engine
        assert not hasattr(engine, 'log')
        assert not hasattr(engine, '__testvar__')
        assert not hasattr(engine, 'another_var')

        engine.includeme(config)

        config.include.assert_called_once_with('foo')
        mock_resolve.assert_called_once_with('foo')
        assert not hasattr(engine, 'log')
        assert not hasattr(engine, '__testvar__')
        assert hasattr(engine, 'another_var')
