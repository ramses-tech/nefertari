Getting started
===============

1. Create your project in a virtualenv directory (see the `pyramid documentation <http://docs.pylonsproject.org/docs/pyramid/en/latest/narr/project.html>`_ if you've never done that before)

.. code-block:: shell

    $ virtualenv my_project
    $ source my_project/bin/activate
    $ cd my_project
    $ pip install nefertari
    $ pcreate -s nefertari_starter my_project
    $ pserve local.ini
