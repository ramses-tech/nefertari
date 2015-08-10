Authentication & Security
=========================

Authentication Mechanism
------------------------

Set ``auth = true`` in you .ini file to turn enable authentication. Nefertari currently uses the default Pyramid "auth ticket" cookie mechanism.


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
