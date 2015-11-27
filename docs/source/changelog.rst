Changelog
=========

* :release:`0.6.1 <2015-11-18>`
* :bug:`-` Added 'event.instance' to 'event' object to access newly created object (if object is returned by view method)
* :bug:`-` Fixed a bug with GET '/auth/logout'
* :bug:`-` 'request.user' is now set to None when using 'auth = False'

* :release:`0.6.0 <2015-10-07>`
* :feature:`-` Event system is now crud-based as opposed to db-based
* :feature:`-` Refactored field processors to use the new event system
* :feature:`-` Removed unnecessary extra '__confirmation' parameter from PATCH/PUT/DELETE collection requests
* :feature:`-` Nested relationships are now indexed in bulk in Elasticsearch
* :feature:`-` Added '_hidden_fields' model attribute to hide fields while remaining editable (e.g. password)
* :bug:`- major` Fixed a bug causing polymorchic collections to always return 403
* :bug:`- major` Fixed nested relationships not respecting '_auth_fields'
* :support:`-` Added support for `'nefertari-guards' <https://nefertari-guards.readthedocs.org/>`_

* :release:`0.5.1 <2015-09-02>`
* :bug:`-` Fixed '_self' param for ``/api/users/self`` convience route
* :bug:`-` Fixed a bug when using reserved query params with GET tunneling
* :bug:`-` Fixed an error preventing RelationshipFields' backrefs to be set as _nested_relationships
* :bug:`-` Fixed a bug allowing to update hidden fields
* :bug:`-` Simplified ACLs (refactoring)

* :release:`0.5.0 <2015-08-19>`
* :feature:`-` Renamed field 'self' to '_self'
* :feature:`-` Refactored authentication
* :feature:`-` Renamed setting `debug` to `enable_get_tunneling`
* :feature:`-` Added the ability to apply processors on 'Relationship' fields and their backrefs
* :feature:`-` Model's save()/update()/delete()/_delete_many()/_update_many() methods now require self.request to be passed for '_refresh_index' parameter to work
* :feature:`-` Routes can now have the same member/collection name. E.g. root.add('staff', 'staff', ...)
* :bug:`- major` Fixed sorting by 'id' when two ES-based models have two different 'id' field types
* :bug:`- major` Removed unused 'id' field from 'AuthUserMixin'
* :bug:`- major` Fixed bug with full-text search ('?q=') when used in combination with field search ('&<field>=')
* :bug:`- major` Fixed 40x error responses returning html, now all responses are json-formatted
* :bug:`- major` Fixed formatting error when using `_fields` query parameter
* :bug:`- major` Fixed duplicate records when querying ES aggregations by '_type'
* :bug:`- major` Fixed 400 error returned when querying resources with id in another format than the id field used in URL schema, e.g. ``/api/<collection>/<string_instead_of_integer>``, it now returns 404
* :bug:`- major` Fixed `_count` querying not respecting ``public_max_limit`` .ini setting
* :bug:`- major` Fixed error response when aggregating hidden fields with ``auth = true``, it now returns 403

* :release:`0.4.1 <2015-07-07>`
* :bug:`-` Fixed a bug when setting ``cors.allow_origins = *``
* :bug:`-` Fixed errors in http methods HEAD/OPTIONS response
* :bug:`-` Fixed response of http methods POST/PATCH/PUT not returning created/updated objects
* :support:`- backported` Added support for Elasticsearch polymorphic collections accessible at ``/api/<collection_1>,<collection_N>``

* :release:`0.4.0 <2015-06-14>`
* :support:`-` Added python3 support
* :feature:`-` Added ES aggregations
* :feature:`-` Reworked ES bulk queries to use 'elasticsearch.helpers.bulk'
* :feature:`-` Added ability to empty listfields by setting them to "" or null

* :release:`0.3.4 <2015-06-09>`
* :bug:`-` Fixed bug whereby `_count` would throw exception when authentication was enabled

* :release:`0.3.3 <2015-06-05>`
* :bug:`-` Fixed bug with posting multiple new relations at the same time

* :release:`0.3.2 <2015-06-03>`
* :bug:`-` Fixed bug with Elasticsearch indexing of nested relationships
* :bug:`-` Fixed race condition in Elasticsearch indexing by adding the optional '_refresh_index' query parameter

* :release:`0.3.1 <2015-05-27>`
* :bug:`-` Fixed PUT to replace all fields and PATCH to update some
* :bug:`-` Fixed posting to singular resources e.g. ``/api/users/<username>/profile``
* :bug:`-` Fixed ES mapping error when values of field were all null

* :release:`0.3.0 <2015-05-18>`
* :support:`-` Step-by-step 'Getting started' guide
* :bug:`- major` Fixed several issues related to Elasticsearch indexing
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
* :support:`-` Initial release after two years of development as 'Presto'. Now with database engines! Originally extracted and generalized from the Brandicted API which only used MongoDB.
