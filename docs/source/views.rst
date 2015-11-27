Configuring Views
=================

.. code-block:: python

    from nefertari.view import BaseView
    from example_api.models import Story


    class StoriesView(BaseView):
        Model = Story

        def index(self):
            return self.get_collection_es()

        def show(self, **kwargs):
            return self.context

        def create(self):
            story = self.Model(**self._json_params)
            return story.save(self.request)

        def update(self, **kwargs):
            story = self.Model.get_item(
                id=kwargs.pop('story_id'), **kwargs)
            return story.update(self._json_params, self.request)

        def replace(self, **kwargs):
            return self.update(**kwargs)

        def delete(self, **kwargs):
            story = self.Model.get_item(
                id=kwargs.pop('story_id'), **kwargs)
            story.delete(self.request)

        def delete_many(self):
            es_stories = self.get_collection_es()
            stories = self.Model.filter_objects(es_stories)

            return self.Model._delete_many(stories, self.request)

        def update_many(self):
            es_stories = self.get_collection_es()
            stories = self.Model.filter_objects(es_stories)

            return self.Model._update_many(
                stories, self._json_params, self.request)

* ``index()`` called upon ``GET`` request to a collection, e.g. ``/collection``
* ``show()`` called upon ``GET`` request to a collection-item, e.g. ``/collection/<id>``
* ``create()`` called upon ``POST`` request to a collection
* ``update()`` called upon ``PATCH`` request to a collection-item
* ``replace()`` called upon ``PUT`` request to a collection-item
* ``delete()`` called upon ``DELETE`` request to a collection-item
* ``update_many()`` called upon ``PATCH`` request to a collection or filtered collection
* ``delete_many()`` called upon ``DELETE`` request to a collection or filtered collection


Polymorphic Views
-----------------

Set ``elasticsearch.enable_polymorphic_query = true`` in your .ini file to enable this feature. Polymorphic views are views that return two or more comma-separated collections, e.g.`/api/<collection_1>,<collection_N>`. They are dynamic which means that they do not need to be defined in your code.


Other Considerations
--------------------

It is recommended that your views reside in a package:
    In this case, each module of that package would contain all views of any given root-level route. Alternatively, ou can explicitly provide a view name, or a view class as a ``view`` keyword argument to ``resource.add()`` in your project's ``main`` function.

For singular resources:
    there is no need to define ``index()``

Each view must define the following property:
    *Model*: model being served by the current view. Must be set at class definition for features to work properly. E.g.:

.. code-block:: python


    from nefertari.view import BaseView
    from example_api.models import Story

    class StoriesView(BaseView):
        Model = Story

Optional properties:
    *_json_encoder*: encoder to encode objects to JSON. Database-specific encoders are available at ``nefertari.engine.JSONEncoder``
