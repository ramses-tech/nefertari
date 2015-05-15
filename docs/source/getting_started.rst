Getting started
===============

**1. Create a Pyramid "starter" project** in a virtualenv directory (see the `pyramid documentation <http://docs.pylonsproject.org/docs/pyramid/en/latest/narr/project.html>`_)::

    $ pcreate -s starter MyProject
    $ cd MyProject
    $ pip install -e .

Install nefertari and the database backend you want to use, e.g. sqla or mongodb::

    $ pip install nefertari
    $ pip install nefertari-<engine>

**2. Add a few settings** to your .ini file under the ``[app:main]`` section

.. code-block:: ini

    # Elasticsearh settings
    elasticsearch.hosts = localhost:9200
    elasticsearch.sniff = false
    elasticsearch.index_name = MyProject
    elasticsearch.index.disable = false

    # enable/disable authentication
    auth = false

    # Max number of objects returned to unauthenticated users (if auth = true)
    public_max_limit = 100

    # Set '<nefertari_engine>' (e.g. nefertari_sqla or nefertari_mongodb)
    nefertari.engine = <nefertari_engine>

.. code-block:: ini

    # For sqla:
    sqlalchemy.url = postgresql://localhost:5432/MyProject

.. code-block:: ini

    # For mongo:
    mongodb.host = localhost
    mongodb.port = 27017
    mongodb.db = MyProject

**3. Replace the file** `myproject/__init__.py`

.. code-block:: python

    from pyramid.config import Configurator


    def main(global_config, **settings):
        from .models import Item

        config = Configurator(settings=settings)
        config.include('nefertari.engine')
        config.include('nefertari')
        config.include('nefertari.elasticsearch')

        # Include your `models` modules
        config.include('myproject.models')

        root = config.get_root_resource()

        root.add(
            'myitem', 'myitems',
            id_name='myitem_' + Story.pk_field())


        # Use the engine helper to bootstrap the db
        from nefertari.engine import setup_database
        setup_database(config)

        config.commit()
        # Launch the server in the way that works for you
        return config.make_wsgi_app()

**4. Replace the file** `myproject/views.py`

.. code-block:: python

    from nefertari.view import BaseView
    from nefertari.engine import JSONEncoder
    from nefertari.elasticsearch import ES
    from nefertari.json_httpexceptions import (
        JHTTPCreated, JHTTPOk)

    from .models import Item


    class ItemsView(BaseView):
        _model_class = Item

        def index(self):
            return ES('Item').get_collection(**self._query_params)

        def show(self, **kwargs):
            return self.context

        def create(self):
            story = Item(**self._json_params)
            story.arbitrary_object = ArbitraryObject()
            story.save()
            pk_field = Item.pk_field()
            return JHTTPCreated(
                location=self.request._route_url(
                    'items', getattr(story, pk_field)),
                resource=story.to_dict(),
                request=self.request,
            )

        def update(self, **kwargs):
            pk_field = Item.pk_field()
            kwargs = self.resolve_kwargs(kwargs)
            story = Item.get_resource(**kwargs).update(self._json_params)

            return JHTTPOk(
                location=self.request._route_url(
                'items',
                getattr(story, pk_field))
            )

        def delete(self, **kwargs):
            kwargs = self.resolve_kwargs(kwargs)
            Item._delete(**kwargs)

            return JHTTPOk()

**5. Create the file** `myproject/models.py`

.. code-block:: python

    from nefertari import engine as eng
    from nefertari.engine import ESBaseDocument

    def includeme(config):
        pass


    class Item(ESBaseDocument):
        __tablename__ = 'items'

        id = eng.IdField(primary_key=True)
        name = eng.StringField()
        description = eng.TextField()



Notes:

When using SQLA, each view must define the following properties:
    * *_model_class*: class of the model that is being served by this view.

Optional properties:
    * *_json_encoder*: encoder to encode objects to JSON. Database-specific encoders are available at ``nefertari.engine.JSONEncoder``.

Your views should reside in a package and each module of that package should contain views for a particular root level route. In our example, the ``users`` route view must be at ``views.users.UsersView``.

Note that in case of a singular resource (i.e. Likes), there is no "index" view and "show" returns only the one item.
Also, note that "delete", "update" and other actions that would normally require an id, do not in Nefertari, because there is only one object being referenced.

4. Define your models using abstractions imported from 'nefertari.engine'. For more information on abstractions, see :doc:`engines/index` section.

5. Run your app with ``pserve settings_file.ini`` and request the routes you defined.

