from __future__ import absolute_import
import json
import logging
from functools import partial

import elasticsearch
from elasticsearch import helpers
import six

from nefertari.utils import (
    dictset, dict2obj, process_limit, split_strip)
from nefertari.json_httpexceptions import (
    JHTTPBadRequest, JHTTPNotFound, exception_response)
from nefertari import engine

log = logging.getLogger(__name__)

RESERVED = [
    '_start',
    '_limit',
    '_page',
    '_fields',
    '_count',
    '_sort',
    '_raw_terms',
    '_search_fields',
]


class IndexNotFoundException(Exception):
    pass


class ESHttpConnection(elasticsearch.Urllib3HttpConnection):
    def _catch_index_error(self, response):
        """ Catch and raise index errors which are not critical and thus
        not raised by elasticsearch-py.
        """
        code, headers, raw_data = response
        if not raw_data:
            return
        data = json.loads(raw_data)
        if not data or not data.get('errors'):
            return
        try:
            error_dict = data['items'][0]['index']
            message = error_dict['error']
        except (KeyError, IndexError):
            return
        raise exception_response(400, detail=message)

    def perform_request(self, *args, **kw):
        try:
            if log.level == logging.DEBUG:
                msg = str(args)
                if len(msg) > 512:
                    msg = msg[:300] + '...TRUNCATED...' + msg[-212:]
                log.debug(msg)
            resp = super(ESHttpConnection, self).perform_request(*args, **kw)
        except Exception as e:
            log.error(e.error)
            status_code = e.status_code
            if status_code == 404:
                raise IndexNotFoundException()
            if status_code == 'N/A':
                status_code = 400
            raise exception_response(
                status_code,
                detail=six.b('Elasticsearch error'),
                extra=dict(data=e))
        else:
            self._catch_index_error(resp)
            return resp


def includeme(config):
    Settings = dictset(config.registry.settings)
    ES.setup(Settings)
    ES.create_index()


def _bulk_body(documents_actions, refresh_index=None):
    kwargs = {
        'client': ES.api,
        'actions': documents_actions,
    }
    refresh_provided = refresh_index is not None
    refresh_enabled = ES.settings.asbool('enable_refresh_query')
    if refresh_provided and refresh_enabled:
        kwargs['refresh'] = refresh_index

    executed_num, errors = helpers.bulk(**kwargs)
    log.info('Successfully executed {} Elasticsearch action(s)'.format(
        executed_num))
    if errors:
        raise Exception('Errors happened when executing Elasticsearch '
                        'actions'.format('; '.join(errors)))


def process_fields_param(fields):
    """ Process 'fields' ES param.

    * Fields list is split if needed
    * '_type' field is added, if not present, so the actual value is
      displayed instead of 'None'
    * '_source=False' is returned as well, so document source is not
      loaded from ES. This is done because source is not used when
      'fields' param is provided
    """
    if not fields:
        return fields
    if isinstance(fields, six.string_types):
        fields = split_strip(fields)
    if '_type' not in fields:
        fields.append('_type')
    return {
        'fields': fields,
        '_source': False,
    }


def apply_sort(_sort):
    _sort_param = []

    if _sort:
        for each in [e.strip() for e in _sort.split(',')]:
            if each.startswith('-'):
                _sort_param.append(each[1:] + ':desc')
            elif each.startswith('+'):
                _sort_param.append(each[1:] + ':asc')
            else:
                _sort_param.append(each + ':asc')

    return ','.join(_sort_param)


def build_terms(name, values, operator='OR'):
    return (' %s ' % operator).join(['%s:%s' % (name, v) for v in values])


def build_qs(params, _raw_terms='', operator='AND'):
    # if param is _all then remove it
    params.pop_by_values('_all')

    terms = []

    for k, v in params.items():
        if k.startswith('__'):
            continue
        if type(v) is list:
            terms.append(build_terms(k, v))
        else:
            terms.append('%s:%s' % (k, v))

    terms = sorted([term for term in terms if term])
    _terms = (' %s ' % operator).join(terms) + _raw_terms

    return _terms


class _ESDocs(list):
    def __init__(self, *args, **kw):
        self._total = 0
        self._start = 0
        super(_ESDocs, self).__init__(*args, **kw)


class ES(object):
    api = None
    settings = None

    @classmethod
    def src2type(cls, source):
        return source.lower()

    @classmethod
    def setup(cls, settings):
        ES.settings = settings.mget('elasticsearch')
        ES.settings.setdefault('chunk_size', 500)

        try:
            _hosts = ES.settings.hosts
            hosts = []
            for (host, port) in [
                    split_strip(each, ':') for each in split_strip(_hosts)]:
                hosts.append(dict(host=host, port=port))

            params = {}
            if ES.settings.asbool('sniff'):
                params = dict(
                    sniff_on_start=True,
                    sniff_on_connection_fail=True
                )

            ES.api = elasticsearch.Elasticsearch(
                hosts=hosts, serializer=engine.ESJSONSerializer(),
                connection_class=ESHttpConnection, **params)
            log.info('Including ElasticSearch. %s' % ES.settings)

        except KeyError as e:
            raise Exception(
                'Bad or missing settings for elasticsearch. %s' % e)

    def __init__(self, source='', index_name=None, chunk_size=None):
        self.doc_type = self.src2type(source)
        self.index_name = index_name or ES.settings.index_name
        if chunk_size is None:
            chunk_size = ES.settings.asint('chunk_size')
        self.chunk_size = chunk_size

    @classmethod
    def create_index(cls, index_name=None):
        index_name = index_name or ES.settings.index_name
        try:
            ES.api.indices.exists([index_name])
        except IndexNotFoundException:
            ES.api.indices.create(index_name)

    @classmethod
    def setup_mappings(cls, force=False):
        """ Setup ES mappings for all existing models.

        This method is meant to be run once at application lauch.
        ES._mappings_setup flag is set to not run make mapping creation
        calls on subsequent runs.

        Use `force=True` to make subsequent calls perform mapping
        creation calls to ES.
        """
        if getattr(ES, '_mappings_setup', False) and not force:
            log.debug('ES mappings have been already set up for currently '
                      'running application. Call `setup_mappings` with '
                      '`force=True` to perform mappings set up again.')
            return
        log.info('Setting up ES mappings for all existing models')
        models = engine.get_document_classes()
        try:
            for model_name, model_cls in models.items():
                if getattr(model_cls, '_index_enabled', False):
                    es = ES(model_cls.__name__)
                    es.put_mapping(body=model_cls.get_es_mapping())
        except JHTTPBadRequest as ex:
            raise Exception(ex.json['extra']['data'])
        ES._mappings_setup = True

    def delete_mapping(self):
        ES.api.indices.delete_mapping(
            index=self.index_name,
            doc_type=self.doc_type,
        )

    def put_mapping(self, body, **kwargs):
        ES.api.indices.put_mapping(
            doc_type=self.doc_type,
            body=body,
            index=self.index_name,
            **kwargs)

    def process_chunks(self, documents, operation):
        """ Apply `operation` to chunks of `documents` of size
        `self.chunk_size`.

        """
        chunk_size = self.chunk_size
        start = end = 0
        count = len(documents)

        while count:
            if count < chunk_size:
                chunk_size = count
            end += chunk_size

            bulk = documents[start:end]
            operation(documents_actions=bulk)

            start += chunk_size
            count -= chunk_size

    def prep_bulk_documents(self, action, documents):
        if not isinstance(documents, list):
            documents = [documents]

        docs_actions = []
        for doc in documents:
            if not isinstance(doc, dict):
                raise ValueError(
                    'Document type must be `dict` not a `{}`'.format(
                        type(doc).__name__))

            if '_type' in doc:
                _doc_type = self.src2type(doc['_type'])
            else:
                _doc_type = self.doc_type

            doc_action = {
                '_op_type': action,
                '_index': self.index_name,
                '_type': _doc_type,
                '_id': doc['id'],
                '_source': doc,
            }

            docs_actions.append(doc_action)

        return docs_actions

    def _bulk(self, action, documents, refresh_index=None):
        if not documents:
            log.debug('Empty documents: %s' % self.doc_type)
            return

        documents_actions = self.prep_bulk_documents(action, documents)

        if action == 'index':
            for doc in documents_actions:
                doc_data = doc.get('_source', {})
                if 'timestamp' in doc_data:
                    doc['_timestamp'] = doc_data['timestamp']

        if documents_actions:
            operation = partial(_bulk_body, refresh_index=refresh_index)
            self.process_chunks(
                documents=documents_actions,
                operation=operation)
        else:
            log.warning('Empty body')

    def index(self, documents, refresh_index=None):
        """ Reindex all `document`s. """
        self._bulk('index', documents, refresh_index)

    def index_missing_documents(self, documents, refresh_index=None):
        """ Index documents that are missing from ES index.

        Determines which documents are missing using ES `mget` call which
        returns a list of document IDs as `documents`. Then missing
        `documents` from that list are indexed.
        """
        log.info('Trying to index documents of type `{}` missing from '
                 '`{}` index'.format(self.doc_type, self.index_name))
        if not documents:
            log.info('No documents to index')
            return
        query_kwargs = dict(
            index=self.index_name,
            doc_type=self.doc_type,
            fields=['_id'],
            body={'ids': [d['id'] for d in documents]},
        )
        try:
            response = ES.api.mget(**query_kwargs)
        except IndexNotFoundException:
            indexed_ids = set()
        else:
            indexed_ids = set(
                d['_id'] for d in response['docs'] if d.get('found'))
        documents = [d for d in documents if str(d['id']) not in indexed_ids]

        if not documents:
            log.info('No documents of type `{}` are missing from '
                     'index `{}`'.format(self.doc_type, self.index_name))
            return

        self._bulk('index', documents, refresh_index)

    def delete(self, ids, refresh_index=None):
        if not isinstance(ids, list):
            ids = [ids]

        documents = [{'id': _id, '_type': self.doc_type} for _id in ids]
        self._bulk('delete', documents, refresh_index=refresh_index)

    def get_by_ids(self, ids, **params):
        if not ids:
            return _ESDocs()

        __raise_on_empty = params.pop('__raise_on_empty', False)
        fields = params.pop('_fields', [])

        _limit = params.pop('_limit', len(ids))
        _page = params.pop('_page', None)
        _start = params.pop('_start', None)
        _start, _limit = process_limit(_start, _page, _limit)

        docs = []
        for _id in ids:
            docs.append(
                dict(
                    _index=self.index_name,
                    _type=self.src2type(_id['_type']),
                    _id=_id['_id']
                )
            )

        params = dict(
            body=dict(docs=docs)
        )
        if fields:
            fields_params = process_fields_param(fields)
            params.update(fields_params)

        documents = _ESDocs()
        documents._nefertari_meta = dict(
            start=_start,
            fields=fields,
        )

        try:
            data = ES.api.mget(**params)
        except IndexNotFoundException:
            if __raise_on_empty:
                raise JHTTPNotFound(
                    '{}({}) resource not found (Index does not exist)'.format(
                        self.doc_type, params))
            documents._nefertari_meta.update(total=0)
            return documents

        for _d in data['docs']:
            try:
                _d = _d['fields'] if fields else _d['_source']
            except KeyError:
                msg = "ES: '%s(%s)' resource not found" % (
                    _d['_type'], _d['_id'])
                if __raise_on_empty:
                    raise JHTTPNotFound(msg)
                else:
                    log.error(msg)
                    continue

            documents.append(dict2obj(dictset(_d)))

        documents._nefertari_meta.update(
            total=len(documents),
        )

        return documents

    def build_search_params(self, params):
        params = dictset(params)

        _params = dict(
            index=self.index_name,
            doc_type=self.doc_type
        )

        if 'body' not in params:
            query_string = build_qs(
                params.remove(RESERVED),
                params.get('_raw_terms', ''))
            if query_string:
                _params['body'] = {
                    'query': {
                        'query_string': {
                            'query': query_string
                        }
                    }
                }
            else:
                _params['body'] = {"query": {"match_all": {}}}

        if '_limit' not in params:
            raise JHTTPBadRequest('Missing _limit')

        _params['from_'], _params['size'] = process_limit(
            params.get('_start', None),
            params.get('_page', None),
            params['_limit'])

        if '_sort' in params:
            _params['sort'] = apply_sort(params['_sort'])

        if '_fields' in params:
            _params['fields'] = params['_fields']

        if '_search_fields' in params:
            search_fields = params['_search_fields'].split(',')
            search_fields.reverse()
            search_fields = [s + '^' + str(i) for i, s in
                             enumerate(search_fields, 1)]
            _params['body']['query']['query_string']['fields'] = search_fields

        return _params

    def do_count(self, params):
        # params['fields'] = []
        params.pop('size', None)
        params.pop('from_', None)
        params.pop('sort', None)
        try:
            return ES.api.count(**params)['count']
        except IndexNotFoundException:
            return 0

    def aggregate(self, **params):
        """ Perform aggreration

        Arguments:
            :_aggregations_params: Dict of aggregation params. Root key is an
                aggregation name. Required.
            :__raise_on_empty: Boolean indicating whether to raise exception
                when IndexNotFoundException exception happens. Optional,
                defaults to False.
            :_search_type: Type of search to use. Optional, defaults to
                'count'. You might want to provide this argument explicitly
                when performing nested aggregations on buckets.
        """
        _aggregations_params = params.pop('_aggregations_params', None)
        __raise_on_empty = params.pop('__raise_on_empty', False)
        _search_type = params.pop('_search_type', 'count')

        if not _aggregations_params:
            raise Exception('Missing _aggregations_params')

        # Set limit so ES won't complain. It is ignored in the end
        params['_limit'] = 0
        search_params = self.build_search_params(params)
        search_params.pop('size', None)
        search_params.pop('from_', None)
        search_params.pop('sort', None)

        search_params['search_type'] = _search_type
        search_params['body']['aggregations'] = _aggregations_params

        log.debug('Performing aggregation: {}'.format(_aggregations_params))
        try:
            response = ES.api.search(**search_params)
        except IndexNotFoundException:
            if __raise_on_empty:
                raise JHTTPNotFound(
                    'Aggregation failed: Index does not exist')
            return {}

        try:
            return response['aggregations']
        except KeyError:
            raise JHTTPNotFound('No aggregations returned from ES')

    def get_collection(self, **params):
        __raise_on_empty = params.pop('__raise_on_empty', False)

        if 'body' in params:
            _params = params
        else:
            _params = self.build_search_params(params)

        if '_count' in params:
            return self.do_count(_params)

        fields = _params.pop('fields', '')
        if fields:
            fields_params = process_fields_param(fields)
            _params.update(fields_params)

        documents = _ESDocs()
        documents._nefertari_meta = dict(
            start=_params['from_'],
            fields=fields)

        try:
            data = ES.api.search(**_params)
        except IndexNotFoundException:
            if __raise_on_empty:
                raise JHTTPNotFound(
                    '{}({}) resource not found (Index does not exist)'.format(
                        self.doc_type, params))
            documents._nefertari_meta.update(
                total=0, took=0)
            return documents

        for da in data['hits']['hits']:
            _d = da['fields'] if fields else da['_source']
            _d['_score'] = da['_score']
            documents.append(dict2obj(_d))

        documents._nefertari_meta.update(
            total=data['hits']['total'],
            took=data['took'],
        )

        if not documents:
            msg = "%s(%s) resource not found" % (self.doc_type, params)
            if __raise_on_empty:
                raise JHTTPNotFound(msg)
            else:
                log.debug(msg)

        return documents

    def get_resource(self, **kw):
        __raise = kw.pop('__raise_on_empty', True)

        params = dict(
            index=self.index_name,
            doc_type=self.doc_type
        )
        params.setdefault('ignore', 404)
        params.update(kw)

        try:
            data = ES.api.get_source(**params)
        except IndexNotFoundException:
            if __raise:
                raise JHTTPNotFound(
                    "{}({}) resource not found (Index does not exist)".format(
                        self.doc_type, params))
            data = {}

        if not data:
            msg = "'%s(%s)' resource not found" % (self.doc_type, params)
            if __raise:
                raise JHTTPNotFound(msg)
            else:
                log.debug(msg)

        return dict2obj(data)

    def get(self, **kw):
        kw['__raise_on_empty'] = kw.pop('__raise', False)
        return self.get_resource(**kw)

    @classmethod
    def index_refs(cls, db_obj, refresh_index=None):
        for model_cls, documents in db_obj.get_reference_documents():
            if getattr(model_cls, '_index_enabled', False) and documents:
                cls(model_cls.__name__).index(
                    documents, refresh_index=refresh_index)
