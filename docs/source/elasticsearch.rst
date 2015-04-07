Elasticsearch Support
=====================

Nefertari uses `Elasticsearch <https://www.elastic.co/products/elasticsearch>`_ behind the scenes for most read/GET views.

Making requests
---------------

For models which subclass ESBaseDocument in your project, you may pass various  parameters in the URL to use the search API. See the list of parameters on the `nefertari-example project's readme <https://github.com/brandicted/nefertari-example>`_.


Indexation script
-----------------

In nefertari/scripts you will find es.py, which can be used to manually index models from your database engine to Elasticsearch.

You can run it like so::
	
	$ cd nefertari/scripts
	$ ./es.py --help

The options available are:

**config**: specify ini file to use (required). E.g.::

	$ ./es.py --config ../local.ini

**quiet**: "quiet mode" (surpress output). E.g.::

	$ ./es.py --quiet

**models**: list of dotted paths of models to index. Models must be subclasses of ESBaseDocument.  E.g.::

	$ ./es.py --models example_api.model.story

**params**: URL-encoded parameters for each module.

**index**: Specify name of index. E.g. the slug at the end of http://localhost:9200/example_api

**chunk**: Chunk size.

**force**: Force indexation, even of existing documents (defaults to False).