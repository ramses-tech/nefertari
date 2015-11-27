Getting started
===============

Create your project in a virtualenv directory (see the `virtualenv documentation <https://virtualenv.pypa.io>`_)

.. code-block:: shell

    $ virtualenv my_project
    $ source my_project/bin/activate
    $ pip install nefertari
    $ pcreate -s nefertari_starter my_project
    $ cd my_project
    $ pserve local.ini


Requirements
------------

* Python 2.7, 3.3 or 3.4
* Elasticsearch for Elasticsearch-powered resources (see :any:`models <models>` and :any:`requests <making_requests>`)
* Postgres or Mongodb


Tutorials
---------

- For a more complete example of a Pyramid project using Nefertari, you can take a look at the `Example Project <https://github.com/brandicted/nefertari-example>`_.
