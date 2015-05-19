Authentication & Security
=========================

Set `auth = true` in you .ini file to enable authentication.

Ticket Auth
-----------

Nefertari currently supports the default Pyramid "auth ticket" cookie method of authentication.

Token Auth
----------

(under development)

Visible fields in views
-----------------------

You can control which fields to display to both authenticated users and unauthenticated users by defining `_auth_fields` and `_public_fields` respectively in your models.

ACL API
-------

For authorizing access to specific resources, Nefertari uses standard Pyramid access control lists. `See the documentation on Pyramid ACLs <http://docs.pylonsproject.org/projects/pyramid/en/1.5-branch/narr/security.html>`_ to understand how to extend and customize them.

.. automodule:: nefertari.acl
    :members:

CORS
----

To enable CORS headers, set the following lines in your .ini file:

.. code-block:: ini

    cors.enable = true
    cors.allow_origins = http://localhost
    cors.allow_credentials = true
