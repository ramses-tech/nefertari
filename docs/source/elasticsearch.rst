Elasticsearch Support
=====================

Nefertari uses `Elasticsearch <https://www.elastic.co/products/elasticsearch>`_ behind the scenes for most read/GET views.

Making requests
---------------

For models which subclass ESBaseDocument in your project, you may pass various parameters in the URL to use the search API.

===========================			===========
url parameter						description
===========================			===========
_m=<method>							to force an http method using GET, e.g. _m=POST
q=<keywords>						to filter an ElasticSearch collection using 'keyword ((AND
_fields=<field_list>				to display only specific fields, use - before field names to exclude those fields, e.g. _fields=-descripton
_search_fields=<field_list>			use with ?q=<keywords> to restrict search to specific fields
_limit=<n>							to limit the returned collection to n results (default is 20, max limit is 100 for unauthenticated users)
_sort=<field>						to sort collection by <field>
_start=<n>							to start collection from the <n>th resource
_page=<n>							to start collection at page <n> (n * _limit)
===========================			===========



Indexation script
-----------------

"nefertari.index" console script can be used to manually index models from your database engine to Elasticsearch.

You can run it like so::

    $ nefertari.index --help

The options available are:

**config**: specify ini file to use (required). E.g.::

    $ nefertari.index --config local.ini

**models**: list of dotted paths of models to index. Models must be subclasses of ESBaseDocument.  E.g.::

    $ nefertari.index --config local.ini --models example_api.model.Story

**params**: URL-encoded parameters for each module.

**quiet**: "quiet mode" (surpress output)

**index**: Specify name of index. E.g. the slug at the end of http://localhost:9200/example_api

**chunk**: Index chunk size.

**force**: Force re-indexation of all documents in database engine (defaults to False).