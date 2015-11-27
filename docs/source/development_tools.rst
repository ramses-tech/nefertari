Development Tools
=================

Indexing in Elasticsearch
-------------------------

``nefertari.index`` console script can be used to manually (re-)index models from your database engine to Elasticsearch.

You can run it like so::

    $ nefertari.index --config local.ini --models Model

The available options are:

--config        specify ini file to use (required)
--models        list of models to index. Models must subclass ESBaseDocument.
--params        URL-encoded parameters for each module
--quiet         "quiet mode" (surpress output)
--index         Specify name of index. E.g. the slug at the end of http://localhost:9200/example_api
--chunk         Index chunk size
--force         Force re-indexation of all documents in database engine (defaults to False)

Importing bulk data
-------------------

``nefertari.post2api`` console script can be used to POST data to your api. It may be useful to import data in bulk, e.g. mock data.

You can run it like so::

    $ nefertari.post2api -f ./users.json -u http://localhost:6543/api/users

The available options are:

-f              specify a json file containing an array of json objects
-u              specify the url of the collection you wish to POST to
