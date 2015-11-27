Event Handlers
==============

Nefertari event handler module includes a set of events, maps of events, event handler predicates and helper function to connect it all together. All the objects are contained in ``nefertari.events`` module. Nefertari event handlers use Pyramid event system.


Events
------

``nefertari.events`` defines a set of event classes inherited from ``nefertari.events.RequestEvent``.

There are two types of nefertari events:
    * "Before" events, which are run after view class is instantiated, but before view method is run, and before request is processed
    * "After" events, which are run after view method has been called

Check the API section for a full list of attributes/params events have.

Complete list of events:
    * BeforeIndex
    * BeforeShow
    * BeforeCreate
    * BeforeUpdate
    * BeforeReplace
    * BeforeDelete
    * BeforeUpdateMany
    * BeforeDeleteMany
    * BeforeItemOptions
    * BeforeCollectionOptions
    * AfterIndex
    * AfterShow
    * AfterCreate
    * AfterUpdate
    * AfterReplace
    * AfterDelete
    * AfterUpdateMany
    * AfterDeleteMany
    * AfterItemOptions
    * AfterCollectionOptions

All events are named after camel-cased name of view method they are called around and prefixed with "Before" or "After" depending on the place event is triggered from (as described above). E.g. event classed for view method ``update_many`` are called ``BeforeUpdateMany`` and ``AfterUpdateMany``.


Before vs After
---------------

It is recommended to use ``before`` events to:
    * Transform input
    * Perform validation
    * Apply changes to object that is being affected by request using ``event.set_field_value`` method

And ``after`` events to:
    * Change DB objects which are not affected by request
    * Perform notifications/logging

Note: if a field changed via ``event.set_field_value`` is not affected by request, it will be added to ``event.fields`` which will make any field processors which are connected to this field to be triggered, if they are run after this method call (connected to events after handler that performs method call).


Predicates
----------

**nefertari.events.ModelClassIs**
    Available under ``model`` param when connecting event handlers, it allows to connect event handlers on per-model basis. When event handler is connected using this predicate, it will only be called when ``view.Model`` is the same class or subclass of this param value.


Utilities
----------

**nefertari.events.subscribe_to_events**
    Helper function that allows to connect event handler to multiple events at once. Supports ``model`` event handler predicate param. Available at ``config.subscribe_to_events``. Subscribers are run in order connected.

**nefertari.events.BEFORE_EVENTS**
    Map of ``{view_method_name: EventClass}`` of "Before" events. E.g. one of its elements is ``'index': BeforeIndex``.

**nefertari.events.AFTER_EVENTS**
    Map of ``{view_method_name: EventClass}`` of "AFter" events. E.g. one of its elements is ``'index': AfterIndex``.

**nefertari.events.silent**
    Decorator which marks view class or view method as "silent". Silent view classes and methods don't fire events. In the example below, view ``ItemsView`` won't fire any event. ``UsersView`` won't fire ``BeforeIndex`` and ``AfterIndex`` events but ``BeforeShow`` and ``AfterShow`` events will be fired.

.. code-block:: python

    from nefertari import view, events


    @events.silent
    class ItemsView(view.BaseView):
        ...


    class UsersView(view.BaseView):

        @events.silent
        def index(self):
            ...

        def show(self):
            ...

**nefertari.events.trigger_instead**
    Decorator which allows view method to trigged another event instead of default one. In the example above collection GET requests (``UsersView.index``) will trigger event which corresponds to item PATCH (``update``).

.. code-block:: python

    from nefertari import view, events


    class UsersView(view.BaseView):

        @events.trigger_instead('update')
        def index(self):
            ...


Example
-------

We will use the following example to demonstrate how to connect handlers to events. This handler logs ``request`` to the console.

.. code-block:: python

    import logging
    log = logging.getLogger(__name__)


    def log_request(event):
        log.debug(event.request.body)


We can connect this handler to any of Nefertari events of any requests. E.g. lets log all collection POST after requests are made (view ``create`` method):

.. code-block:: python

    from nefertari import events


    config.subscribe_to_events(
        log_request, [events.AfterCreate])


Or, if we wanted to limit the models for which this handler should be called, we can connect it with a ``model`` predicate:

.. code-block:: python

    from nefertari import events
    from .models import User


    config.subscribe_to_events(
        log_request, [events.AfterCreate],
        model=User)

This way, ``log_request`` event handler will only be called when collection POST request comes at an endpoint which handles the ``User`` model.


API
---

.. autoclass:: nefertari.events.RequestEvent
    :members:
    :private-members:

.. autoclass:: nefertari.events.ModelClassIs
    :members:
    :private-members:

.. autofunction:: nefertari.events.trigger_events

.. autofunction:: nefertari.events.subscribe_to_events

.. autofunction:: nefertari.events.silent

.. autofunction:: nefertari.events.trigger_instead
