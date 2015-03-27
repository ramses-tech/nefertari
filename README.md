# `Nefertari`
Nefertari is a REST API framework sitting on top of [Pyramid](https://github.com/Pylons/pyramid) and [ElasticSearch](https://www.elastic.co/downloads/elasticsearch). She currently offers two backend engines: [SQLA](https://github.com/brandicted/nefertari-sqla) and [MongoDB](https://github.com/brandicted/nefertari-mongodb).

You can read the documentation on [readthedocs]().

### Development
To run tests:
1. Install dev requirements by running ``pip install -r requirements.dev``.
2. Run tests using ``py.test [optional/path/to/tests]`

You can also enable coverage reports when running tests by using ``--cov slashed/path`` option to specify a path to package report for which should be gathered, and ``--cov-report (html|xml|annotate)`` to specify type of coverage report you want to receive.

Use `-v` to make tests output more verbose.
