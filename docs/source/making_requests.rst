Making requests
===============

Query syntax
------------

===============================             ===========
url parameter                               description
===============================             ===========
``_m=<method>``                             to tunnel any http method using GET, e.g. _m=POST
``_limit=<n>``                              to limit the returned collection to <n> results (default: 20, max limit: 100 for unauthenticated users)
``_sort=<field_name>``                      to sort collection by <field_name>
``_start=<n>``                              to start collection from the <n>th resource
``_page=<n>``                               to start collection at page <n> (n * _limit)
``_fields=<field_list>``                    to display only specific fields, use ``-`` before field names to exclude those fields, e.g. ``_fields=-descripton``
===============================             ===========

Query syntax for ElasticSearch
------------------------------

Additional parameters are available when using an ElasticSearch-enabled collection (see **ESBaseDocument** in the `Wrapper API <database_backends.html#wrapper-api>`_ section of this documentation).

===============================             ===========
url parameter                               description
===============================             ===========
``<field_name>=<keywords>``                 to filter a collection using full-text search on <field_name>, ElasticSearch operators [#]_ can be used, e.g. ``?title=foo AND bar``
``q=<keywords>``                            to filter a collection using full-text search on all fields
``_search_fields=<field_list>``             use with ``?q=<keywords>`` to restrict search to specific fields
===============================             ===========

.. [#] The full syntax of ElasticSearch querying is beyond the scope of this documentation. You can read more on the `ElasticSearch Query String Query <http://www.elastic.co/guide/en/elasticsearch/reference/1.x/query-dsl-query-string-query.html>`_ page and more specifically on `Ranges <http://www.elastic.co/guide/en/elasticsearch/reference/1.x/query-dsl-query-string-query.html#_ranges_2>`_ to do things like: ``?date=[2014-01-01 TO *]``
