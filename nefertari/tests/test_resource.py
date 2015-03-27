import unittest
import mock
from webtest import TestApp

from pyramid import testing
from pyramid.config import Configurator
from pyramid.url import route_path

from nefertari.view import BaseView


def get_test_view_class(name=''):
    class View(BaseView):
        def __init__(self, *a, **k):
            BaseView.__init__(self, *a, **k)
            # turning off before and after calls
            self._before_calls = {}
            self._after_calls = {}

        def index(self, **a):
            return name + 'index'

        def show(self, **a):
            return name + 'show'

        def delete(self, **a):
            return name + 'delete'

        def __getattr__(self, attr):
            return lambda *a, **k: name + attr

        def convert_ids2objects(self, *args, **kwargs):
            pass

    return View


def _create_config():
    config = Configurator(autocommit=True)
    config.include('nefertari')
    return config


class Test(unittest.TestCase):
    def setUp(self):
        self.config = _create_config()
        self.config.begin()

    def tearDown(self):
        self.config.end()
        del self.config


class DummyCrudView(object):
    _json_encoder = None

    def __init__(self, request):
        self.request = request

    def index(self, **a):
        return 'index'

    def show(self, **a):
        return 'show'

    def delete(self, **a):
        return 'delete'

    def __getattr__(self, attr):
        return lambda *a, **kw: attr


class TestResourceGeneration(Test):
    def test_basic_resources(self):
        from nefertari.resource import add_resource_routes
        add_resource_routes(self.config, DummyCrudView, 'message', 'messages')

        self.assertEqual(
            '/messages',
            route_path('messages', testing.DummyRequest())
        )
        self.assertEqual(
            '/messages/1',
            route_path('message', testing.DummyRequest(), id=1)
        )

    def test_resources_with_path_prefix(self):
        from nefertari.resource import add_resource_routes

        add_resource_routes(
            self.config,
            DummyCrudView,
            'message',
            'messages',
            path_prefix='/category/{category_id}'
        )

        self.assertEqual(
            '/category/2/messages',
            route_path('messages', testing.DummyRequest(), category_id=2)
        )
        self.assertEqual(
            '/category/2/messages/1',
            route_path('message', testing.DummyRequest(), id=1, category_id=2)
        )

    def test_resources_with_path_prefix_with_trailing_slash(self):
        from nefertari.resource import add_resource_routes
        add_resource_routes(
            self.config,
            DummyCrudView,
            'message',
            'messages',
            path_prefix='/category/{category_id}/'
        )

        self.assertEqual(
            '/category/2/messages',
            route_path('messages', testing.DummyRequest(), category_id=2)
        )
        self.assertEqual(
            '/category/2/messages/1',
            route_path('message', testing.DummyRequest(), id=1, category_id=2)
        )

    def test_resources_with_name_prefix(self):
        from nefertari.resource import add_resource_routes
        add_resource_routes(
            self.config,
            DummyCrudView,
            'message',
            'messages',
            name_prefix="special_"
        )

        self.assertEqual(
            '/messages/1',
            route_path('special_message', testing.DummyRequest(), id=1)
        )


class TestResourceRecognition(Test):
    def setUp(self):
        from nefertari.resource import add_resource_routes
        self.config = _create_config()
        add_resource_routes(
            self.config,
            DummyCrudView,
            'message',
            'messages',
            renderer='string'
        )
        self.config.begin()
        self.app = TestApp(self.config.make_wsgi_app())
        self.collection_path = '/messages'
        self.collection_name = 'messages'
        self.member_path     = '/messages/{id}'
        self.member_name     = 'message'

    def test_get_collection(self):
        self.assertEqual(self.app.get('/messages').body, 'index')

    def test_get_collection_json(self):
        from nefertari.resource import add_resource_routes
        add_resource_routes(
            self.config,
            DummyCrudView,
            'message',
            'messages',
            renderer='json'
        )
        self.assertEqual(self.app.get('/messages').body, '"index"')

    def test_get_collection_nefertari_json(self):
        from nefertari.resource import add_resource_routes
        add_resource_routes(
            self.config,
            DummyCrudView,
            'message',
            'messages',
            renderer='nefertari_json'
        )
        self.assertEqual(self.app.get('/messages').body, '"index"')

    def test_get_collection_no_renderer(self):
        from nefertari.resource import add_resource_routes
        add_resource_routes(self.config, DummyCrudView, 'message', 'messages')
        self.assertRaises(ValueError, self.app.get, '/messages')

    def test_post_collection(self):
        result = self.app.post('/messages').body
        self.assertEqual(result, 'create')

    def test_get_member(self):
        result = self.app.get('/messages/1').body
        self.assertEqual(result, 'show')

    def test_put_member(self):
        result = self.app.put('/messages/1').body
        self.assertEqual(result, 'update')

    def test_delete_member(self):
        result = self.app.delete('/messages/1').body
        self.assertEqual(result, 'delete')


class TestResource(Test):

    def test_default_view(self, *a):
        from nefertari.resource import Resource, default_view

        m = Resource(
            self.config,
            member_name='group_member',
            collection_name='group_members'
        )

        self.assertEqual(
            "nefertari.tests.views.group_members:GroupMembersView",
            default_view(m)
        )

        #singular
        m = Resource(self.config, member_name='group_member')
        self.assertEqual(
            "nefertari.tests.views.group_member:GroupMemberView",
            default_view(m)
        )

    def test_singular_resource(self, *a):
        View = get_test_view_class()
        config = _create_config()
        root = config.get_root_resource()
        root.add('thing', view=View)
        grandpa = root.add('grandpa', 'grandpas', view=View)
        wife = grandpa.add('wife', view=View, renderer='string')
        wife.add('child', 'children', view=View)

        config.begin()
        app = TestApp(config.make_wsgi_app())

        self.assertEqual(
            '/grandpas/1/wife',
            route_path('grandpa:wife', testing.DummyRequest(), grandpa_id=1)
        )

        self.assertEqual(
            '/grandpas/1',
            route_path('grandpa', testing.DummyRequest(), id=1)
        )

        self.assertEqual(
            '/grandpas/1/wife/children/2',
            route_path('grandpa_wife:child', testing.DummyRequest(),
                       grandpa_id=1, id=2)
        )

        self.assertEqual(
            app.put('/grandpas').body,
            app.post('/grandpas', params=dict(_method='PUT')).body
        )

        self.assertEqual(
            app.delete('/grandpas/1').body,
            app.post('/grandpas/1', params=dict(_method='DELETE')).body
        )

        self.assertEqual(
            app.put('/thing').body,
            app.post('/thing', params=dict(_method='PUT')).body
        )

        self.assertEqual(
            app.delete('/thing').body,
            app.post('/thing', params=dict(_method='DELETE')).body
        )

        self.assertEqual(
            app.put('/grandpas/1/wife').body,
            app.post('/grandpas/1/wife', params=dict(_method='PUT')).body
        )

        self.assertEqual(
            app.delete('/grandpas/1/wife').body,
            app.post('/grandpas/1/wife', params=dict(_method='DELETE')).body
        )

        self.assertEqual('"show"', app.get('/grandpas/1').body)
        self.assertEqual('"show"', app.get('/grandpas/1/wife').body)
        self.assertEqual('"show"', app.get('/grandpas/1/wife/children/1').body)

    def test_renderer_override(self, *args):
        # resource.renderer and view._default_renderer are only used
        # when accept header is missing.

        View = get_test_view_class()
        config = _create_config()
        r = config.get_root_resource()

        r.add('thing', 'things', renderer='json', view=View)
        r.add('2thing', '2things', renderer='json', view=View)
        r.add('3thing', '3things', view=View)  # defaults to nefertari_json

        config.begin()
        app = TestApp(config.make_wsgi_app())

        #no headers, user renderer==string.returns string
        self.assertEqual('"index"', app.get('/things').body)

        #header is sting, renderer is string. returns string
        self.assertEqual(
            'index', app.get('/things',
            headers={'ACCEPT': 'text/plain'}).body)

        #header is json, renderer is string. returns json
        self.assertEqual(
            '"index"', app.get('/things',
            headers={'ACCEPT': 'application/json'}).body)

        #no header. returns json
        self.assertEqual('"index"', app.get('/2things').body)

        #header==json, renderer==json, returns json
        self.assertEqual(
            '"index"', app.get('/2things',
            headers={'ACCEPT': 'application/json'}).body)

        #header==text, renderer==json, returns string
        self.assertEqual(
            "index", app.get('/2things',
            headers={'ACCEPT': 'text/plain'}).body)

        # no header, no renderer. uses default_renderer, returns
        # View._default_renderer==nefertari_json
        self.assertEqual('"index"', app.get('/3things').body)

        self.assertEqual(
            '"index"', app.get('/3things',
            headers={'ACCEPT': 'application/json'}).body)

        self.assertEqual(
            'index', app.get('/3things',
            headers={'ACCEPT': 'text/plain'}).body)

        #bad accept.defaults to json
        self.assertEqual(
            '"index"', app.get('/3things',
            headers={'ACCEPT': 'text/blablabla'}).body)

    def test_nonBaseView_default_renderer(self, *a):
        config = _create_config()
        r = config.get_root_resource()
        r.add('ything', 'ythings', view=get_test_view_class())

        config.begin()
        app = TestApp(config.make_wsgi_app())

        self.assertEqual('"index"', app.get('/ythings').body)

    def test_nested_resources(self, *a):
        config = _create_config()
        root = config.get_root_resource()

        aa = root.add('a', 'as', view=get_test_view_class('A'))
        bb = aa.add('b', 'bs', view=get_test_view_class('B'))
        cc = bb.add('c', 'cs', view=get_test_view_class('C'))
        dd = cc.add('d', 'ds', view=get_test_view_class('D'))

        config.begin()
        app = TestApp(config.make_wsgi_app())

        app.get('/as/1/bs/2/cs/3/ds/4')


# @mock.patch('nefertari.resource.add_tunneling')
class TestMockedResource(Test):

    def test_get_root_resource(self, *args):
        from nefertari.resource import Resource

        root = self.config.get_root_resource()
        w = root.add('whatver', 'whatevers', view=get_test_view_class())
        self.assertIsInstance(root, Resource)
        self.assertIsInstance(w, Resource)
        self.assertEqual(root, self.config.get_root_resource())

    def test_resource_repr(self, *args):
        r = self.config.get_root_resource()
        bl = r.add('blabla', view=get_test_view_class())
        assert "Resource(uid='blabla')" == str(bl)

    def test_resource_exists(self, *a):
        r = self.config.get_root_resource()
        r.add('blabla', view=get_test_view_class())
        self.assertRaises(ValueError, r.add, 'blabla')

    def test_get_ancestors(self, *args):
        from nefertari.resource import Resource
        m = Resource(self.config)

        self.assertEqual([], m.ancestors)

        gr = m.add('grandpa', 'grandpas', view=get_test_view_class())
        pa = m.add('parent', 'parents', parent=gr, view=get_test_view_class())
        ch = m.add('child', 'children', parent=pa, view=get_test_view_class())

        self.assertListEqual([gr, pa], ch.ancestors)

    def test_resource_uid(self, *arg):
        from nefertari.resource import Resource
        m = Resource(self.config)
        self.assertEqual(m.uid, '')

        a = m.add('a', 'aa', view=get_test_view_class())
        self.assertEqual('a', a.uid)

        c = a.add('b', 'bb', view=get_test_view_class()).add(
            'c', 'cc', view=get_test_view_class())
        self.assertEqual('a:b:c', c.uid)

    @mock.patch('nefertari.resource.add_resource_routes')
    def test_add_resource_routes(self, *arg):
        from nefertari.resource import Resource

        View = get_test_view_class()
        m_add_resource_routes = arg[0]

        m = Resource(self.config)
        g = m.add('grandpa', 'grandpas', view=View)

        m_add_resource_routes.assert_called_once_with(
            self.config,
            View,
            'grandpa',
            'grandpas',
            factory=None,
            http_cache=0,
            auth=False,
            renderer=View._default_renderer,
            path_prefix=''
        )

        pr = g.add('parent', 'parents', view=View)

        m_add_resource_routes.assert_called_with(
            self.config,
            View,
            'parent',
            'parents',
            factory=None,
            http_cache=0,
            auth=False,
            path_prefix='grandpas/{grandpa_id}',
            name_prefix='grandpa:',
            renderer=View._default_renderer
        )

        ch = pr.add('child', 'children', view=View)

        m_add_resource_routes.assert_called_with(
            self.config,
            View,
            'child',
            'children',
            factory=None,
            http_cache=0,
            auth=False,
            path_prefix='grandpas/{grandpa_id}/parents/{parent_id}',
            name_prefix='grandpa_parent:',
            renderer=View._default_renderer
        )

        self.assertEqual(ch.uid, 'grandpa:parent:child')

    @mock.patch('nefertari.resource.add_resource_routes')
    def test_add_resource_routes_with_parent_param(self, *arg):
        from nefertari.resource import Resource
        View = get_test_view_class()
        m_add_resource_routes = arg[0]

        m = Resource(self.config)
        g = m.add('grandpa', 'grandpas', view=View)

        m.add('parent', 'parents', parent='grandpa', view=View)
        m_add_resource_routes.assert_called_with(
            self.config,
            View,
            'parent',
            'parents',
            factory=None,
            auth=False,
            http_cache=0,
            path_prefix='grandpas/{grandpa_id}',
            name_prefix='grandpa:',
            renderer='nefertari_json',
        )

        gm = m.add('grandma', 'grandmas', view=View)

        pa = m.add('parent', 'parents', parent=gm, view=View)
        m_add_resource_routes.assert_called_with(
            self.config,
            View,
            'parent',
            'parents',
            factory=None,
            auth=False,
            http_cache=0,
            path_prefix='grandmas/{grandma_id}',
            name_prefix='grandma:',
            renderer=View._default_renderer,
        )
        pa.add('child', 'children', parent='grandpa:parent', view=View)
        m_add_resource_routes.assert_called_with(
            self.config,
            View,
            'child',
            'children',
            factory=None,
            auth=False,
            http_cache=0,
            path_prefix='grandpas/{grandpa_id}/parents/{parent_id}',
            name_prefix='grandpa_parent:',
            renderer=View._default_renderer
        )

    @mock.patch('nefertari.resource.add_resource_routes')
    def test_add_resource_routes_from(self, *args):
        View = get_test_view_class()
        root = self.config.get_root_resource()
        gm = root.add('grandma', 'grandmas', view=View)
        pa = gm.add('parent', 'parents', view=View)
        boy = pa.add('boy', 'boys', view=View)
        grchild = boy.add('child', 'children', view=View)
        girl = pa.add('girl', 'girls', view=View)

        self.assertEqual(len(root.resource_map), 5)

        gp = root.add('grandpa', 'grandpas', view=View)
        gp.add_from(pa, view=View)

        self.assertEqual(
            pa.children[0],
            root.resource_map['grandma:parent:boy']
        )
        self.assertEqual(
            gp.children[0].children[1],
            root.resource_map['grandpa:parent:girl']
        )
        self.assertEqual(len(root.resource_map), 10)

        # make sure these are not same objects but copies.
        self.assertNotEqual(girl, gp.children[0].children[1])
