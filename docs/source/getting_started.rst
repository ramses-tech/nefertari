Getting started
===============

To get started, follow these steps:

0. Install nefertari::

    pip install nefertari


1. `First, create a normal Pyramid app <http://docs.pylonsproject.org/docs/pyramid/en/latest/narr/firstapp.html#firstapp-chapter>`_. In the "main" module, import nefertari and then declare your resources like so::

    from pyramid.config import Configurator
    from pyramid.authorization import ACLAuthorizationPolicy
    from pyramid.authentication import AuthTktAuthenticationPolicy
    from nefertari.acl import RootACL


    def main(global_config, **settings):
        # Nefertari encourages using ACLAuthorizationPolicy and provides a few
        # base ACL classes. Choice of authentication policy is completely
        # up to you.
        config = Configurator(
            settings=settings,
            authorization_policy=ACLAuthorizationPolicy(),
            authentication_policy=AuthTktAuthenticationPolicy(),
            root_factory=RootACL,
        )

        # Include 'nefertari.engine' to let her perform the engine setup
        config.include('nefertari.engine')

        # Include nefertari and elasticsearch
        config.include('nefertari')
        config.include('nefertari.elasticsearch')

        # Include your models modules after inclusion of 'nefertari.engine'
        config.include('my_app.models')

        # Declare your resources
        root = config.get_root_resource()
        user = root.add('user', 'users', factory='my_app.acl.UsersACL')
        user_story = user.add('story', 'stories')
        user_story.add('likes')

        # Use the engine helper to bootstrap the db
        from nefertari.engine import setup_database
        setup_database(config)

        config.commit()
        # Launch the server in the way that works for you
        return config.make_wsgi_app()


And here is the content of our ``acl.py``. Check out ACLs that are included in Nefertari in :doc:`acls` section::

    from nefertari.acl import GuestACL
    from .models import User

    class UserACL(GuestACL):
        __context_class__ = User


2. Add Nefertari settings to your settings file (e.g. ``local.ini``) under ``[app:your_app_name]`` section::

.. code-block:: ini

    # Set 'nefertari.engine' to the dotted path of the engine you want.
    nefertari.engine = nefertari.engine.sqla

    # Elasticsearh settings
    elasticsearch.hosts = localhost:9200
    elasticsearch.sniff = false
    elasticsearch.index_name = my_app
    elasticsearch.index.disable = false

    # Dependine on the engine you chose, provide database-specific settings.
    # E.g. for sqla:
    sqlalchemy.url = postgresql://user:password@host:port/dbname

    # For mongo:
    mongodb.host = localhost
    mongodb.port = 27017
    mongodb.db = dbname

    # Other nefertari settings
    # Auth enabled/disabled
    auth = false
    # Debug enabled/disabled
    debug = true
    # Max age of the static cache
    static_cache_max_age = 7200
    # Max number of objects returned from public APIs
    public_max_limit = 100


3. The corresponding views would look something like the following. Defined actions are: index (GET), show (GET), create(POST), update(PUT/PATCH), delete(DELETE)::

.. code-block:: python

    from nefertari.view import BaseView
    from nefertari.engine import JSONEncoder


    class UsersView(BaseView):
        _model_class = User

        def show(self, id):
            return {}

        def create(self):
            return HTTPCreated()

        def index(self):
            return {'data'=['item1', 'item2']}

        def delete(self, id):
            return HTTPOk()


    class UserStoriesView(BaseView):
        _model_class = UserStory

        def index(self, user_id):
            # Get stories here
            stories = []
            return dict(data=stories, count=len(stories))

        def show(self, user_id, id):
            # Get a particular story here
            return story_dict

        def delete(self, user_id, id):
            return HTTPOK()


    class UserStoryLikesView(BaseView):
        _model_class = UserStoryLike

        def show(self, user_id, story_id):
            # Get a particular story like here
            return user_story_like_dict

        def delete(self, user_id, story_id):
            return HTTPOK()


Each view must define the following properties:

    * *_model_class*: class of the model that is being served by this view.

Optional properties:

    * *_json_encoder*: encoder to encode objects to JSON. Engine-specific encoders are available at ``nefertari.engine.JSONEncoder``.

Your views should sit in a package and each module of that package should contain views for a particular root level route. In our example, the ``users`` route view must be at ``views.users.UsersView``.


If its not defined in your view, Nefertari will return HTTPMethodNotAllowed by default.
Note that in case of a singular resource (i.e. Likes), there is no "index" view and "show" returns only the one item.
Also, note that "delete", "update" and other actions that would normally require an id, do not in Nefertari, because there is only one object being referenced.

4. Define your models using abstractions imported from 'nefertari.engine'. For more information on abstractions, see :doc:`engines/index` section.

5. Run your app with ``pserve settings_file.ini`` and request the routes you defined.


In case you need to tunnel PUT,PATCH and DELETE via POST in a browser one must use "_method=<METHOD_NAME>"  or the shorthand "_m" along with other POST parameters as if they were normal URL params. E.g. http://myapi.com/api/stories?_m=POST&name=stuff&user=bob".
