Authentication & Authorization
==============================

Nefertari currently supports the default Pyramid "auth ticket" cookie method of authentication.

For authorizing access to specific resources, Nefertari uses standard Pyramid access control lists. `See the documentation on Pyramid ACLs <http://docs.pylonsproject.org/projects/pyramid/en/1.5-branch/narr/security.html>`_ to understand how to extend and customize them.

ACL API
-------

.. automodule:: nefertari.acl
    :members:
