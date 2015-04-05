Engines
=======

Engines in the context of Nefertari are wrappers/abstractions around existing backend ORMs/interfaces/modules etc. There are currently two engines available:

* 'sqla' engine is based at SQLAlchemy.
* 'mongodb' engine is based at MongoEngine

These engines are meant to provide almost exact API and be easily switchable without side-effects.


Engines API:


* `SQLA Engine <http://nefertari-sqla.readthedocs.org/en/latest/>`_
* `MongoDB Engine <http://nefertari-mongodb.readthedocs.org/en/latest/>`_


Common API
----------

.. if this changes, it must be updated in docs for nefertari{-sqla|mongodb}
.. TODO: figure out how to include common elements in templates

**BaseMixin**
    Mixin with a most of the API of *BaseDocument*. *BaseDocument* subclasses from this mixin.

**BaseDocument**
    Base for regular models defined in your application. Just subclass it to define your model's fields. Relevant attributes:
        * **_auth_fields**: String names of fields meant to be displayed to authenticated users.
        * **_public_fields**: String names of fields meant to be displayed to non-authenticated users.
        * **_nested_relationships**: String names of relationship fields that should be included in JSON data of an object as full included documents. If relationship field is not present in this list, this field's value in JSON will be an object's ID or list of IDs.

**ESBaseDocument**
    Subclass of *BaseDocument* instances of which are indexed on create/update/delete.

**ESMetaclass**
    Document metaclass which is used in *ESBaseDocument* to enable automatic indexation to Elasticsearch of documents.

**get_document_cls(name)**
    Helper function used to get the class of document by the name of the class.

**JSONEncoder**
    JSON encoder that should be used to encode output of views.

**ESJSONSerializer**
    JSON encoder used to encode documents prior indexing them in Elasticsearch.

**relationship_fields**
    Tuple of classes that represent relationship fields in specific engine.

**is_relationship_field(field, model_cls)**
    Helper function to determine whether *field* is a relationship field at *model_cls* class.

**relationship_cls(field, model_cls)**
    Return class which is pointed to by relationship field *field* from model *model_cls*.

Field abstractions
-------------------

* BigIntegerField
* BooleanField
* DateField
* DateTimeField
* ChoiceField
* FloatField
* IntegerField
* IntervalField
* BinaryField
* DecimalField
* PickleField
* SmallIntegerField
* StringField
* TextField
* TimeField
* UnicodeField
* UnicodeTextField
* Relationship
* PrimaryKeyField
* ForeignKeyField
