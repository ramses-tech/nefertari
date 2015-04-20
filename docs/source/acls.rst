Authentication & Authorization
==============================

Nefertari currently supports the default Pyramid "auth ticket" cookie method of authentication.

For authorizing access to specific resources, Nefertari uses standard Pyramid access control lists. `See the documentation on Pyramid ACLs to understand how to <http://docs.pylonsproject.org/projects/pyramid/en/1.5-branch/narr/security.html>`_.

ACL API
-------

.. automodule:: nefertari.acl
    :members:
