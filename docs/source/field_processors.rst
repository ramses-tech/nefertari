Field processors
================

Nefertari allows users to define functions that accept field data and return modified field value, may perform validation or perform other actions related to field.

These functions are called "field processors". They are set up per-field and are called when request comes into application that modifies the field for which processor is set up (when field is present in request JSON).


Usage basics
------------

Nefertari field processors support consists of ``nefertari.events.add_field_processors`` function which is used to connect processors to model fields. The function is accessible through Pyramid Configurator instance.

``nefertari.events.add_field_processors`` expects following parameters:

**processors**
    Sequence of processor functions.

**model**
    Model class for field if which processors are registered.

**field**
    Field name for which processors are registered.


Nefertari passes following parameters to processors:

**new_value**
    New value of of field.

**instance**
    Instance affected by request. Is None when set of items is updated in bulk and when item is created.

**field**
    Instance of nefertari.utils.data.FieldData instance containing data of changed field.

**request**
    Current Pyramid Request instance.

**model**
    Model class affected by request.

**event**
    Underlying event object. Should be used to edit other fields of instance using ``event.set_field_value(value, field_name)``.


Processors are called in order they are passed to ``nefertari.events.add_field_processors``. Each processor must return processed value which is used a input for next processor if present.


Examples
--------

Having subscriber that strips and lowers value:

.. code-block:: python

    # processors.py
    def lower_strip(**kwargs):
        return kwargs['new_value'].lower().strip()

And basic model:

.. code-block:: python

    # models.py
    from nefertari import engine

    class Item(engine.BaseDocument):
        __tablename__ = 'stories'
        id = engine.IdField(primary_key=True)
        name = engine.StringField(required=True)

And we want to make sure ``Item.name`` is always lowercase and stripped, we can connect ``lower_strip`` to ``Item.name`` field using ``nefertari.events.add_field_processors`` function like so:

.. code-block:: python

    # __init__.py
    from .models import Item
    from .processors import lower_strip

    # Get access to Pyramid configurator
    ...

    config.add_field_processors([lower_strip], model=Item, field='name')

When set up as above, ``lower_strip`` processor will be called each time application gets a request that changes ``Item.name`` field.

To edit other fields of instance, ``event.set_field_value`` method should be used. E.g. if we have fields ``due_date`` and ``days_left`` and we connect processor defined below to field ``due_date``, we can update ``days_left`` from it:

.. code-block:: python

    from .helpers import parse_data
    from datetime import datetime

    def calculate_days_left(**kwargs):
        parsed_date = parse_data(kwargs['new_value'])
        days_left = (parsed_date-datetime.now()).days
        event = kwargs['event']
        event.set_field_value(days_left, 'days_left')
        return kwargs['new_value']

API
---

.. autoclass:: nefertari.events.FieldIsChanged
    :members:
    :private-members:

.. autofunction:: nefertari.events.add_field_processors
