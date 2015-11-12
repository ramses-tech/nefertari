Authentication & Security
=========================

In order to enable authentication, add the ``auth`` paramer to your .ini file:

.. code-block:: ini

    auth = true

Nefertari currently uses the default Pyramid "auth ticket" cookie mechanism.


Custom User Model
-----------------

When authentication is enabled, Nefertari uses its own `User` model. This model has 4 fields by default: username, email, password and groups (list field with values 'admin' and 'user'). However, this model can be extanded.

.. code-block:: python

    from nefertari import engine as eng
    from nefertari.authentication.models import AuthUserMixin
    from nefertari.engine import BaseDocument


    class User(AuthUserMixin, BaseDocument):
        __tablename__ = 'users'

        first_name = eng.StringField(max_length=50, default='')
        last_name = eng.StringField(max_length=50, default='')


Visible Fields in Views
-----------------------

You can control which fields to display by defining the following properties on your models:

**_auth_fields**
    Lists fields to be displayed to authenticated users.

**_public_fields**
    Lists fields to be displayed to all users including unauthenticated users.

**_hidden_fields**
    Lists fields to be hidden but remain editable (as long as user has permission), e.g. password.


Permissions
-----------

This section describes permissions used by nefertari, their relation to view methods and HTTP methods. These permissions should be used when defining ACLs.

To make things easier to grasp, let's imagine we have an application that defines a view which handles all possible requests under ``/products`` route. We are going to use this example to make permissions description more obvious.

Following lists nefertari permissions along with HTTP methods and view methods they correspond to:

**view**
    * Collection GET (``GET /products``). View method ``index``
    * Item GET (``GET /products/1``) View method ``show``
    * Collection HEAD (``HEAD /products``). View method ``index``
    * Item HEAD (``HEAD /products/1``). View method ``show``

**create**
    * Collection POST (``POST /products``). View method ``create``

**update**
    * Collection PATCH (``PATCH /products``). View method ``update_many``
    * Collection PUT (``PUT /products``). View method ``update_many``
    * Item PATCH (``PATCH /products/1``). View method ``update``
    * Item PUT (``PUT /products/1``) View method ``replace``

**delete**
    * Collection DELETE (``DELETE /products``). View method ``delete_many``
    * Item DELETE (``DELETE /products/1``). View method ``delete``

**options**
    * Collection OPTIONS (``OPTIONS /products``). View method ``collection_options``
    * Item OPTIONS (``OPTIONS /products/1``). View method ``item_options``


ACL API
-------

For authorizing access to specific resources, Nefertari uses standard Pyramid access control lists. `See the documentation on Pyramid ACLs <http://docs.pylonsproject.org/projects/pyramid/en/1.5-branch/narr/security.html>`_ to understand how to extend and customize them.

Considerations:
    * An item will inherit its collection's permissions if the item's permissions are not specified in an ACL class
    * If you create an ACL class for your document that does something like give the document.owner edit permissions, then you can’t rely on this setting to be respected during collection operation. in other words, only if you walk up to the item via a URL will this permission setting be applied.

.. automodule:: nefertari.acl
    :members:


Advanced ACLs
-------------

For more advanced ACLs, you can look into using `nefertari-guards <https://github.com/brandicted/nefertari-guards>`_ in you project. This package stores ACLs at the object level, making it easier to build multi-tenant applications using a single data store.


CORS
----

To enable CORS headers, set the following lines in your .ini file:

.. code-block:: ini

    cors.enable = true
    cors.allow_origins = http://localhost
    cors.allow_credentials = true
