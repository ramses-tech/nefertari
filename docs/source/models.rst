Configuring Models
==================

.. code-block:: python

    from datetime import datetime
    from nefertari import engine as eng
    from nefertari.engine import BaseDocument


    class Story(BaseDocument):
        __tablename__ = 'stories'

        _auth_fields = [
            'id', 'updated_at', 'created_at', 'start_date',
            'due_date', 'name', 'description']
        _public_fields = ['id', 'start_date', 'due_date', 'name']

        id = eng.IdField(primary_key=True)
        updated_at = eng.DateTimeField(onupdate=datetime.utcnow)
        created_at = eng.DateTimeField(default=datetime.utcnow)

        start_date = eng.DateTimeField(default=datetime.utcnow)
        due_date = eng.DateTimeField()

        name = eng.StringField(required=True)
        description = eng.TextField()


Database Backends
-----------------

Nefertari implements database engines on top of two different ORMs: `SQLAlchemy <http://www.sqlalchemy.org>`_ and `MongoEngine <http://mongoengine.org/>`_. These two engines wrap the underlying APIs of each ORM and provide a standardized syntax for using either one, making it easy to switch between them with minimal changes. Each Nefertari engine is maintained in its own repository:

* `nefertari-sqla github repository <https://github.com/ramses-tech/nefertari-sqla>`_
* `nefertari-mongodb github repository <https://github.com/ramses-tech/nefertari-mongodb>`_

Nefertari can either use `Elasticsearch <https://www.elastic.co/products/elasticsearch>`_ (*ESBaseDocument*) or the database engine itself (*BaseDocument*) for reads.

.. code-block:: python

    from nefertari.engine import ESBaseDocument


    class Story(ESBaseDocument):
        (...)

or

.. code-block:: python

    from nefertari.engine import BaseDocument


    class Story(BaseDocument):
        (...)

You can read more about *ESBaseDocument* and *BaseDocument* in the :any:`Wrapper API <wrapper-api>` section below.


.. _wrapper-api:

Wrapper API
-----------

Both database engines used by Nefertari implement a "Wrapper API" for developers who use Nefertari in their project. You can read more about either engine's in their respective documentation:

    * `nefertari-sqla documentation <http://nefertari-sqla.readthedocs.org/>`_
    * `nefertari-mongodb documentation <http://nefertari-mongodb.readthedocs.org/>`_

BaseMixin
    Mixin with most of the API of *BaseDocument*. *BaseDocument* subclasses from this mixin.

BaseDocument
    Base for regular models defined in your application. Just subclass it to define your model's fields. Relevant attributes:

    * `__tablename__`: table name (only required by nefertari-sqla)
    * `_auth_fields`: String names of fields meant to be displayed to authenticated users.
    * `_public_fields`: String names of fields meant to be displayed to non-authenticated users.
    * `_hidden_fields`: String names of fields meant to be hidden but editable.
    * `_nested_relationships`: String names of relationship fields that should be included in JSON data of an object as full included documents. If relationship field is not present in this list, this field's value in JSON will be an object's ID or list of IDs.

ESBaseDocument
    Subclass of *BaseDocument* instances of which are indexed on create/update/delete.

ESMetaclass
    Document metaclass which is used in *ESBaseDocument* to enable automatic indexation to Elasticsearch of documents.

get_document_cls(name)
    Helper function used to get the class of document by the name of the class.

JSONEncoder
    JSON encoder that should be used to encode output of views.

ESJSONSerializer
    JSON encoder used to encode documents prior indexing them in Elasticsearch.

relationship_fields
    Tuple of classes that represent relationship fields in specific engine.

is_relationship_field(field, model_cls)
    Helper function to determine whether *field* is a relationship field at *model_cls* class.

relationship_cls(field, model_cls)
    Return class which is pointed to by relationship field *field* from model *model_cls*.


Field Types
-----------

This is the list of all the available field types:

* BigIntegerField
* BinaryField
* BooleanField
* ChoiceField
* DateField
* DateTimeField
* DecimalField
* DictField
* FloatField
* ForeignKeyField (ignored/not required when using mongodb)
* IdField
* IntegerField
* IntervalField
* ListField
* PickleField
* Relationship
* SmallIntegerField
* StringField
* TextField
* TimeField
* UnicodeField
* UnicodeTextField
