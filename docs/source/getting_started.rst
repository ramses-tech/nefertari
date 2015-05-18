Getting started
===============

**1. Create a Pyramid "starter" project** in a virtualenv directory (see the `pyramid documentation <http://docs.pylonsproject.org/docs/pyramid/en/latest/narr/project.html>`_ if you've never done that before)

.. code-block:: shell

    $ mkvirtualenv MyProject
    $ pip install nefertari
    $ pcreate -s starter MyProject
    $ cd MyProject
    $ pip install -e .

Install the database backend of your choice, e.g. sqla or mongodb

.. code-block:: shell

    $ pip install nefertari-<engine>


**2. Add a few settings** to development.ini, inside the ``[app:main]`` section

.. code-block:: ini

    # Elasticsearh settings
    elasticsearch.hosts = localhost:9200
    elasticsearch.sniff = false
    elasticsearch.index_name = myproject
    elasticsearch.index.disable = false

    # disable authentication
    auth = false

    # Set '<nefertari_engine>' (e.g. nefertari_sqla or nefertari_mongodb)
    nefertari.engine = <nefertari_engine>

.. code-block:: ini

    # For sqla:
    sqlalchemy.url = postgresql://localhost:5432/myproject

.. code-block:: ini

    # For mongo:
    mongodb.host = localhost
    mongodb.port = 27017
    mongodb.db = myproject


**3. Replace the file** `myproject/__init__.py`

.. code-block:: python

    from pyramid.config import Configurator


    def main(global_config, **settings):

        config = Configurator(settings=settings)
        config.include('nefertari.engine')
        config.include('nefertari')
        config.include('nefertari.elasticsearch')

        # Include your `models` modules
        config.include('myproject.models')

        root = config.get_root_resource()

        from .models import Item
        root.add(
            'myitem', 'myitems',
            view='myproject.views.ItemsView')

        # Use the engine helper to bootstrap the db
        from nefertari.engine import setup_database
        setup_database(config)

        config.commit()
        # Launch the server in the way that works for you
        return config.make_wsgi_app()


**4. Replace the file** `myproject/views.py`

.. code-block:: python

    from nefertari.view import BaseView
    from nefertari.elasticsearch import ES
    from nefertari.json_httpexceptions import (
        JHTTPCreated, JHTTPOk)

    from .models import Item


    class ItemsView(BaseView):
        _model_class = Item

        def index(self):
            self._query_params.process_int_param('_limit', 20)
            return ES('Item').get_collection(**self._query_params)

        def show(self, **kwargs):
            return ES('Item').get_resource(**kwargs)

        def create(self):
            story = Item(**self._json_params)
            story.save()
            pk_field = Item.pk_field()
            return JHTTPCreated(
                resource=story.to_dict(),
                request=self.request,
            )

        def update(self, **kwargs):
            pk_field = Item.pk_field()
            story = Item.get_resource(**kwargs).update(self._json_params)
            return JHTTPOk()

        def delete(self, **kwargs):
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


**5. Run your app**

.. code-block:: shell

    $ pserve development.ini
