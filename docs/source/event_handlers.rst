Event Handlers
==============

Nefertari event handler module includes a set of events, maps of events, subscriber predicates and helper function to connect it all together. All the objects are contained in ``nefertari.events`` module. Nefertari event handlers use Pyramid event system.


Events
------

``nefertari.events`` defines a set of event classes inherited from ``nefertari.events.RequestEvent``.

There are two types of nefertari events:
    * "Before" events, which are run after view class is instantiated, but before view method is run, thus before request is processed.
    * "After" events, which are run after view method was called.

All events are named after camel-cased name of view method they are called around and prefixed with "Before" or "After" depending on the place event is triggered from (as described above). E.g. event classed for view method ``update_many`` are called ``BeforeUpdateMany`` and ``AfterUpdateMany``.

Check the API section for a full list of attributes/params events have.

It's recommended to use ``before`` events to:
    * Transform input
    * Perform validation
    * Apply changes to object that is being affected by request using ``event.set_field_value`` method.

And ``after`` events to:
    * Change DB objects which are not affected by request.
    * Perform notifications/logging.

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


Predicates
----------

Nefertari defines and sets up following subscriber predicates:

**nefertari.events.ModelClassIs**
    Available under ``model`` param when connecting subscribers, it allows to connect subscribers on per-model basis. When subscriber is connected using this predicate, it will only be called when ``view.Model`` is the same class or subclass of this param value.

**nefertari.events.FieldIsChanged**
    Available under ``field`` param when connecting subscribers, it allows to connect subscribers on per-field basis. When subscriber is connected using this predicate, it will only be called when value of this param is present in request JSON body.


Utilities
----------

**nefertari.events.subscribe_to_events**
    Helper function that allows to connect subscriber to multiple events at once. Supports ``model`` and ``field`` subscriber predicate params. Available at ``config.subscribe_to_events``. Subscribers are run in order connected.

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


Examples
--------

Having subscriber that logs request body:

.. code-block:: python

    import logging
    log = logging.getLogger(__name__)

    def log_request(event):
        log.debug(event.request.body)

**Having access to configurator**, we can connect it to any of Nefertari events. E.g. lets log all collection POST requests (view ``create`` method):

.. code-block:: python

    from nefertari import events

    config.subscribe_to_events(log_request, [events.AfterCreate])

Connected this way ``log_request`` subscriber will be called after every collection POST request.

In case we want to limit models for which subscriber will be called, we can connect subscriber with a ``model`` predicate:

.. code-block:: python

    from nefertari import events
    from .models import User

    config.subscribe_to_events(
        log_request, [events.AfterCreate],
        model=User)

Connected this way ``log_request`` subscriber will only be called when collection POST request comes at endpoint which handles our ``User`` model.

We can also use ``field`` predicate to make subscriber run only when particular field is present in request JSON body. E.g. if we only want to log collection POST requests for model ``User`` which contain ``first_name`` field, we connect subscriber like so:

.. code-block:: python

    from nefertari import events
    from .models import User

    config.subscribe_to_events(
        log_request, [events.AfterCreate],
        model=User, field='first_name')


Predicate ``fields`` can also be used without ``model`` predicate. E.g. if we want to log all POST request bodies of when they have field ``favourite`` we should connect subscriber like so:

.. code-block:: python

    from nefertari import events
    from .models import User

    config.subscribe_to_events(
        log_request, [events.AfterCreate],
        field='favourite')


API
---

.. autoclass:: nefertari.events.RequestEvent
    :members:
    :private-members:

.. autoclass:: nefertari.events.ModelClassIs
    :members:
    :private-members:

.. autoclass:: nefertari.events.FieldIsChanged
    :members:
    :private-members:

.. autofunction:: nefertari.events.trigger_events

.. autofunction:: nefertari.events.subscribe_to_events

.. autofunction:: nefertari.events.silent
