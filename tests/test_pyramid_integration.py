import unittest
import mock


class TestPyramidIntegration(unittest.TestCase):

    def test_includeme(self):
        from nefertari import includeme

        config = mock.Mock()
        config.registry.settings = {'auth': True}
        includeme(config)

        self.assertEqual(3, config.add_directive.call_count)
        self.assertEqual(2, config.add_renderer.call_count)
        root = config.get_root_resource()
        assert root.auth
