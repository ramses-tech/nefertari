Database Backends
=================

Nefertari implements database engines on top of two different ORMs: `SQLAlchemy <http://www.sqlalchemy.org>`_ and `MongoEngine <http://mongoengine.org/>`_. As such, Nefertari can be used with exising models implemented using either mapper library.

These two engines wrap the underlying APIs of each ORM and provide a standardized syntax for using either one, making it easy to switch between them with minimal changes.

Each Nefertari engine is developed in its own repository:

* `SQLA Engine <http://nefertari-sqla.readthedocs.org/en/latest/>`_
* `MongoDB Engine <http://nefertari-mongodb.readthedocs.org/en/latest/>`_


Wrapper API
-----------

Both of the database engines used by Nefertari implement the exact same "common API" for developers to use within a Nefertari project. Use the following base classes in your project to leverage the powers of Nefertari. To see them in action, check out the `example project <https://github.com/brandicted/nefertari-example>`_.

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
