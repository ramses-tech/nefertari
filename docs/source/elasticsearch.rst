Elasticsearch Support
=====================

Nefertari uses `Elasticsearch <https://www.elastic.co/products/elasticsearch>`_ behind the scenes for most read/GET views.

Making requests
---------------

For models which subclass ESBaseDocument in your project, you may pass various  parameters in the URL to use the search API. See the list of parameters on the `nefertari-example project's readme <https://github.com/brandicted/nefertari-example>`_.


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