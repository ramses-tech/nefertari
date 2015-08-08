Making requests
===============


Query syntax
------------

Query parameters can be used on either GET, PATCH, PUT or DELETE requests.

===============================             ===========
url parameter                               description
===============================             ===========
``_m=<method>``                             to tunnel any http method using GET, e.g. _m=POST [#]_
``_limit=<n>``                              to limit the returned collection to <n> results (default: 20, max limit: 100 for unauthenticated users)
``_sort=<field_name>``                      to sort collection by <field_name>
``_start=<n>``                              to start collection from the <n>th resource
``_page=<n>``                               to start collection at page <n> (n * _limit)
``_fields=<field_list>``                    to display only specific fields, use ``-`` before field names to exclude those fields, e.g. ``_fields=-descripton``
===============================             ===========


Query syntax for ElasticSearch
------------------------------

Additional parameters are available when using an ElasticSearch-enabled collection (see **ESBaseDocument** in the `Wrapper API <database_backends.html#id1>`_ section of this documentation).

========================================            ===========
url parameter                                       description
========================================            ===========
``<field_name>=<keywords>``                         to filter a collection using full-text search on <field_name>, ES operators [#]_ can be used, e.g. ``?title=foo AND bar``
``q=<keywords>``                                    to filter a collection using full-text search on all fields
``_search_fields=<field_list>``                     use with ``?q=<keywords>`` to restrict search to specific fields
``_refresh_index=true``                             to refresh the ES index after performing the operation [#]_
``_aggregations.<dot_notation_object>``             to use ES search aggregations, e.g. ``?_aggregations.my_agg.terms.field=tag`` [#]_
========================================            ===========

Updating listfields
-------------------

Items in listfields can be removed using "-" prefix.

PATCH ``/api/<collection>/<id>``

.. code-block:: json

    {
        "<list_field_name>": [-<item>]
    }

Items can be both added and removed at the same time.

PATCH ``/api/<collection>/<id>``

.. code-block:: json

    {
        "<list_field_name>": [<item_to_add>,-<item_to_remove>]
    }

Listfields can be emptied by setting their value to "" or null.

PATCH ``/api/<collection>/<id>``

.. code-block:: json

    {
        "<list_field_name>": ""
    }


Updating collections
--------------------

If update_many() is defined in your view, you will be able to update a single field across an entire collection or a filtered collection. E.g.

PATCH `/api/<collection>?q=<keywords>`

.. code-block:: json

    {
        "<field_name>": "<new_value>"
    }


Deleting collections
--------------------

Similarly, if delete_many() is defined, you will be able to delete whole collections or filtered collections. E.g.

DELETE `/api/<collection>?_missing_=<field_name>`


.. [#] To update listfields and dictfields, you can use the following syntax: ``_m=PATCH&<listfield>.<value>&<dictfield>.<key>=<value>``
.. [#] The full syntax of ElasticSearch querying is beyond the scope of this documentation. You can read more on the `ElasticSearch Query String Query documentation <https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html>`_ to do things like fuzzy search: ``?name=fuzzy~`` or date range search: ``?date=[2015-01-01 TO *]``
.. [#] Set ``elasticsearch.enable_refresh_query = true`` in your .ini file to enable this feature. This parameter only works with POST, PATCH, PUT and DELETE methods. Read more on `ElasticSearch Bulk API documentation <https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-bulk.html#bulk-refresh>`_.
.. [#] Set ``elasticsearch.enable_aggregations = true`` in your .ini file to enable this feature. You can also use the short name `_aggs`. Read more on `ElasticSearch Aggregations <https://www.elastic.co/guide/en/elasticsearch/reference/current/search-aggregations.html>`_.
