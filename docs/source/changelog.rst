Changelog
=========

* :release:`0.3.2 <2015-06-03>`
* :bug:`-` Fixed bug with Elasticsearch indexing of nested relationships
* :bug:`-` Fixed race condition in Elasticsearch indexing

* :release:`0.3.1 <2015-05-27>`
* :bug:`-` Fixed PUT to replace all fields and PATCH to update some
* :bug:`-` Fixed posting to singular resources e.d. /api/users/<username>/profile
* :bug:`-` Fixed ES mapping error when values of field were all null

* :release:`0.3.0 <2015-05-18>`
* :support:`-` Step-by-step 'Getting started' guide
* :bug:`- major` Fixed several issues related to ElasticSearch indexing
* :support:`-` Increased test coverave
* :feature:`-` Added ability to PATCH/DELETE collections
* :feature:`-` Implemented API output control by field (apply_privacy wrapper)

* :release:`0.2.1 <2015-04-21>`
* :bug:`-` Fixed URL parsing for DictField and ListField values with _m=VERB options

* :release:`0.2.0 <2015-04-07>`
* :feature:`-` Added script to index Elasticsearch models
* :feature:`-` Started adding tests
* :support:`-` Listing on PyPI
* :support:`-` Improved docs

* :release:`0.1.1 <2015-04-01>`
* :support:`-` Initial release after two years of development as "Presto". Now with database engines! Originally extracted and generalized from the Brandicted API which only used MongoDB.
