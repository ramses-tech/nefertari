Configuring Views
=================

Introduction
------------

It is recommended that your views reside in a package. In this case, each module of that package would contain all views of any given root-level route. Alternatively, ou can explicitly provide a view name, or a view class as ``view`` keyword argument to ``resource.add()`` in your project's ``main`` function. In the case of a singular resource, there is no need to define ``index`` and ``show`` returns only one item.

* *index*: called upon ``GET`` request to a collection, e.g. ``/collection``
* *show*: called upon ``GET`` request to a collection-item, e.g. ``/collection/<id>``
* *create*: called upon ``POST`` request to a collection
* *update*: called upon ``PATCH`` request to a collection-item
* *replace*: called upon ``PUT`` request to a collection-item
* *delete*: called upon ``DELETE`` request to a collection-item
* *update_many*: called upon ``PATCH`` request to a collection or filtered collection, e.g. ``/collection?_exists_=<field>``
* *delete_many*: called upon ``DELETE`` request to a collection or filtered collection


Polymorphic Views
-----------------

Set ``elasticsearch.enable_polymorphic_query = true`` in your .ini file to enable this feature. Polymorphic views are views that return two or more comma-separated collections, e.g.`/api/<collection_1>,<collection_N>`. They are dynamic which means that they do not need to be defined in your code.


Notes
-----

When using SQLA, each view must define the following properties:
    * *Model*: model being served by the current view

Optional properties:
    * *_json_encoder*: encoder to encode objects to JSON. Database-specific encoders are available at ``nefertari.engine.JSONEncoder``
