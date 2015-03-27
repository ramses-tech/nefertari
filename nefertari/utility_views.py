from pyramid.view import view_config

import nefertari
from nefertari.json_httpexceptions import *
from nefertari import wrappers
from nefertari.view import BaseView


log = logging.getLogger(__name__)


@view_config(name='options_view', request_method='OPTIONS',
             route_name='options')
class OptionsView(object):
    all_methods = set(['GET', 'HEAD', 'POST', 'OPTIONS', 'PUT', 'DELETE',
                       'PATCH', 'TRACE'])

    def __init__(self, request):
        self.request = request

    def __call__(self):
        request = self.request

        request.response.headers['Allow'] = ', '.join(self.all_methods)

        if 'Access-Control-Request-Method' in request.headers:
            request.response.headers['Access-Control-Allow-Methods'] = \
                ', '.join(self.all_methods)

        if 'Access-Control-Request-Headers' in request.headers:
            request.response.headers['Access-Control-Allow-Headers'] = \
                'origin, x-requested-with, content-type'

        return request.response


class EngineView(BaseView):
    def __init__(self, context, request):
        super(EngineView, self).__init__(context, request)
        self._params.process_int_param('_limit', 20)

        def add_self(**kwargs):
            result = kwargs['result']
            request = kwargs['request']

            try:
                for each in result['data']:
                    each['self'] = "%s?id=%s" % (
                        request.current_route_url(), each['id'])
            except KeyError:
                pass

            return result

        self.add_after_call('show', add_self)
        # Wrap in a dict so it acts as "index"
        self.add_after_call('show', wrappers.wrap_in_dict(self.request), pos=0)

    def show(self, id):
        return self._model_class.get_collection(**self._params)

    def delete(self, id):
        objs = self._model_class.get_collection(**self._params)

        if self.needs_confirmation():
            return objs

        count = self._model_class.count(objs)
        self._model_class._delete_many(objs)
        return JHTTPOk("Deleted %s %s objects" % (count, id))


LOGNAME_MAP = dict(
    NOTSET=logging.NOTSET,
    DEBUG=logging.DEBUG,
    INFO=logging.INFO,
    WARNING=logging.WARNING,
    ERROR=logging.ERROR,
    CRITICAL=logging.CRITICAL,
)


class LogLevelView(BaseView):
    def __init__(self, *arg, **kw):
        super(LogLevelView, self).__init__(*arg, **kw)

        self.name = self.request.matchdict.get('id', 'root')
        if self.name == 'root':
            self.log = logging.getLogger()
        else:
            self.log = logging.getLogger(self.name)

    def setlevel(self, level):
        log.info("SET logger '%s' to '%s'" % (self.name, level))
        self.log.setLevel(LOGNAME_MAP[level])

    def show(self, id=None):
        return dict(
            logger=self.name,
            level=logging.getLevelName(self.log.getEffectiveLevel())
        )

    def update(self, id=None):
        level = self._params.keys()[0].upper()
        self.setlevel(level)
        return JHTTPOk()

    def delete(self, id=None):
        self.setlevel('INFO')
        return JHTTPOk()


class SettingsView(BaseView):
    settings = None
    __orig = None

    def __init__(self, *arg, **kw):
        super(SettingsView, self).__init__(*arg, **kw)
        assert(self.settings)
        self.__orig = self.settings.copy()

    def index(self):
        return dict(self.settings)

    def show(self, id):
        return self.settings[id]

    def update(self, id):
        self.settings[id] = self._params['value']
        return JHTTPOk()

    def create(self):
        key = self._params['key']
        value = self._params['value']

        self.settings[key] = value

        return JHTTPCreate()

    def delete(self, id):
        if 'reset' in self._params:
            self.settings[id] = self.request.registry.settings[id]
        else:
            self.settings.pop(id, None)

        return JHTTPOk()

    def delete_many(self):
        if self.needs_confirmation():
            return self.settings.keys()

        for name, val in self.settings.items():
            self.settings[name] = self.__orig[name]

        return JHTTPOk("Reset the settings to original values")
