Field Processors
================

Nefertari allows to define functions that accept field data and return modified field value, may perform validation or perform other actions related to field.

These functions are called "field processors". They are set up per-field and are called when request comes into application that modifies the field for which processor is set up (when the field is present in the request JSON body).


Setup
-----

``nefertari.events.add_field_processors`` is used to connect processors to fields. This function is accessible through Pyramid Configurator instance. Processors are called in the order in which they are defined. Each processor must return the processed value which is used as input for the successive processor (if such processor exists). ``nefertari.events.add_field_processors`` expects the following parameters:

**processors**
    Sequence of processor functions

**model**
    Model class for field if which processors are registered

**field**
    Field name for which processors are registered


Keyword Arguments
-----------------

**new_value**
    New value of of field

**instance**
    Instance affected by request. Is None when set of items is updated in bulk and when item is created. ``event.response`` may be used to access newly created object, if object is returned by view method.

**field**
    Instance of nefertari.utils.data.FieldData instance containing data of changed field.

**request**
    Current Pyramid Request instance

**model**
    Model class affected by request

**event**
    Underlying event object. Should be used to edit other fields of instance using ``event.set_field_value(field_name, value)``


Example
-------

We will use the following example to demonstrate how to connect fields to processors. This processor lowercases values that are passed to it.

.. code-block:: python

    # processors.py
    def lowercase(**kwargs):
        return kwargs['new_value'].lower()


.. code-block:: python

    # models.py
    from nefertari import engine


    class Item(engine.BaseDocument):
        __tablename__ = 'stories'
        id = engine.IdField(primary_key=True)
        name = engine.StringField(required=True)


We want to make sure ``Item.name`` is always lowercase, we can connect ``lowercase`` to ``Item.name`` field using ``nefertari.events.add_field_processors`` like this:

.. code-block:: python

    # __init__.py
    from .models import Item
    from .processors import lowercase


    # Get access to Pyramid configurator
    ...

    config.add_field_processors([lowercase], model=Item, field='name')


``lowercase`` processor will be called each time application gets a request that passes ``Item.name``

You can use the ``event.set_field_value`` helper method to edit other fields from within a processor. E.g. assuming we had the fields ``due_date`` and ``days_left`` and we connected the processor defined below to the field ``due_date``, we can update ``days_left`` from within that same processor:

.. code-block:: python

    from .helpers import parse_data
    from datetime import datetime


    def calculate_days_left(**kwargs):
        parsed_date = parse_data(kwargs['new_value'])
        days_left = (parsed_date-datetime.now()).days
        event = kwargs['event']
        event.set_field_value('days_left', days_left)
        return kwargs['new_value']


Note: if a field changed via ``event.set_field_value`` is not affected by request, it will be added to ``event.fields`` which will make any field processors which are connected to this field to be triggered, if they are run after this method call (connected to events after handler that performs method call).

E.g. if in addition to the above ``calculate_days_left`` processor we had another processor for the ``days_left`` field, ``calculate_days_left`` will make the ``days_left`` processor run because ``event.set_field_value`` is called from within ``calculate_days_left`` field and therefor ``days_left`` is considered "updated/changed".


API
---

.. autoclass:: nefertari.events.FieldIsChanged
    :members:
    :private-members:

.. autofunction:: nefertari.events.add_field_processors
