Why Nefertari?
==============

Nefertari is a tool for making REST APIs using the Pyramid web framework.


Rationale
---------

There are many other libraries that make writing REST APIs easy. Nefertari did not begin as a tool. It was extracted from the API powering `Brandicted <https://brandicted.com/>`_ after almost two years of development. Part of this decision was based on thinking highly of using Elasticsearch-powered views for endpoints, after having had a great experience with it.

We wanted to build powerful REST APIs that are relatively opinionated but still flexible (in order to make easy things easy and hard things possible). We happened to need to use Postgres on a side project, but Brandicted's API only supported MongoDB.

Before extracting Nefertari and turning it into an open source project, we shopped around the Python ecosystem and tested every REST API library/framework to see what would allow us to be as lazy as possible and also allow our APIs to grow bigger over time.

The most convenient option was the beautiful `flask-restless <https://flask-restless.readthedocs.org/en/latest/>`_ by Jeffrey Finkelstein. It depends on SQLAlchemy and does a really good job being super easy to use. We had some subjective reservations about using Flask because of globals and the fact that our closest community members happen to be Pyramid folks. Also, ditching Elasticsearch would have meant needing to write queries in views.

We were also inspired by `pyramid-royal <https://pyramid-royal.readthedocs.org/en/latest/>`_ from our fellow Montreal Python colleague Hadrien David. He showed how traversal is a-ok for matching routes in a tree of resources, which is what REST should be anyway.

However, we had become quite used to the power of Elasticsearch and wanted to retain the option of using it as a first class citizen to power most GET views. Plus we were already using traversal without really thinking. Therefore we decided to add Postgres support via SQLA to our platform, and thus was born Nefertari.


Vision
------

To us, "REST API" means something like "HTTP verbs mapped to CRUD operations on resources described as JSON". We are not trying to do full-on `HATEOAS <https://en.wikipedia.org/wiki/HATEOAS>`_ to satisfy any academic ideal of the REST style. There are quite a few development tasks that can be abstracted away by using our simple definition. This might change in the future when there's more of an ecosystem around client libraries which would know how to browse/consume hypermedia.

By making assumptions about sane defaults, we can eliminate the need for boilerplate to do things like serialization, URL mapping, validation, authentication/authorization, versioning, testing, database queries in views, etc. The only things that should absolutely need to be defined are the resources themselves, and they should just know how to act in a RESTful way by default. They should be configurable to a degree and extendable in special cases. Contrast this idea with something like the `Django Rest Framework <http://www.django-rest-framework.org/#api-guide>`_ where quite a number of things need to be laid out in order to create an endpoint. [#]_

Nefertari is the meat and potatoes of our development stack. Her partner project, Ramses, is the seasoning/sugar/cherry on top! Ramses allows whole production-ready Nefertari apps to be generated at runtime from a simple YAML file specifying the endpoints desired. `Check it out. <https://ramses.readthedocs.org>`_

.. [#] For the record, DRF is pretty badass and we have great respect for its vision and breadth, and the hard work of its community. Laying out a ton of boilerplate can be considered to fall into "flat is better than nested" or "explicit is better than implicit" and might be best for some teams.
