from __future__ import absolute_import
import logging

import elasticsearch

from nefertari.utils import (
    dictset, dict2obj, process_limit, split_strip)
from nefertari.json_httpexceptions import *
from nefertari.engine import ESJSONSerializer

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


class ESHttpConnection(elasticsearch.Urllib3HttpConnection):
    def perform_request(self, *args, **kw):
        try:
            if log.level == logging.DEBUG:
                msg = str(args)
                if len(msg) > 512:
                    msg = msg[:300] + '...TRUNCATED...' + msg[-212:]
                log.debug(msg)

            return super(ESHttpConnection, self).perform_request(*args, **kw)
        except Exception as e:
            if e.status_code == 'N/A':
                e.status_code = 400
            raise exception_response(
                e.status_code,
                detail='elasticsearch error.',
                extra=dict(data=e))


def includeme(config):
    Settings = dictset(config.registry.settings)
    ES.setup(Settings)


def apply_sort(_sort):
    _sort_param = []

    if _sort:
        for each in [e.strip() for e in _sort.split(',')]:
            if each.startswith('-'):
                _sort_param.append(each[1:]+':desc')
            elif each.startswith('+'):
                _sort_param.append(each[1:] + ':asc')
            else:
                _sort_param.append(each + ':asc')

    return ','.join(_sort_param)


def build_terms(name, values, operator='OR'):
    return (' %s ' % operator).join(['%s:%s' % (name, v) for v in values])


def build_qs(params, _raw_terms='', operator='AND'):
    #if param is _all then remove it
    params.pop_by_values('_all')

    terms = []

    for k, v in params.items():
        if k.startswith('__'):
            continue
        if type(v) is list:
            terms.append(build_terms(k, v))
        else:
            terms.append('%s:%s' % (k, v))

    _terms = (' %s ' % operator).join(filter(bool, terms)) + _raw_terms

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

        try:
            _hosts = ES.settings.hosts
            hosts = []
            for (host, port) in [split_strip(each, ':') for each in split_strip(_hosts)]:
                hosts.append(dict(host=host, port=port))

            params = {}
            if ES.settings.asbool('sniff'):
                params = dict(
                    sniff_on_start=True,
                    sniff_on_connection_fail=True
                )

            ES.api = elasticsearch.Elasticsearch(
                hosts=hosts, serializer=ESJSONSerializer(),
                connection_class=ESHttpConnection, **params)
            log.info('Including ElasticSearch. %s' % ES.settings)

        except KeyError as e:
            raise Exception('Bad or missing settings for elasticsearch. %s' % e)

    def __init__(self, source='', index_name=None, chunk_size=100):
        self.doc_type = self.src2type(source)
        self.index_name = index_name or ES.settings.index_name
        self.chunk_size = chunk_size

    def process_chunks(self, documents, operation, chunk_size):
        """ Apply `operation` to chunks of `documents` of size `chunk_size`.

        """
        start = end = 0
        count = len(documents)

        while count:
            if count < chunk_size:
                chunk_size = count
            end += chunk_size

            bulk = documents[start:end]
            operation(bulk)

            start += chunk_size
            count -= chunk_size

    def prep_bulk_documents(self, action, documents):
        if not isinstance(documents, list):
            documents = [documents]

        _docs = []
        for doc in documents:
            if not isinstance(doc, dict):
                raise ValueError('document type must be `dict` not a '
                                 '%s' % (type(doc)))

            if '_type' in doc:
                _doc_type = self.src2type(doc['_type'])
            else:
                _doc_type = self.doc_type

            meta = {
                action: {
                    'action': action,
                    '_index': self.index_name,
                    '_type': _doc_type,
                    '_id': doc['id']
                }
            }

            _docs.append([meta, doc])

        return _docs

    def _bulk(self, action, documents, chunk_size=None):
        chunk_size = chunk_size or self.chunk_size
        if not documents:
            log.debug('empty documents: %s' % self.doc_type)
            return

        documents = self.prep_bulk_documents(action, documents)

        body = []
        for meta, doc in documents:
            action = meta.keys()[0]
            if action == 'delete':
                body += [meta]
            elif action == 'index':
                if 'timestamp' in doc:
                    meta['_timestamp'] = doc['timestamp']
                body += [meta, doc]

        if body:
            # Use chunk_size*2, because `body` is a sequence of
            # meta, document, meta, ...
            self.process_chunks(
                documents=body,
                operation=lambda b: ES.api.bulk(body=b),
                chunk_size=chunk_size*2)
        else:
            log.warning('empty body')

    def index(self, documents, chunk_size=None):
        """ Reindex all `document`. """
        self._bulk('index', documents, chunk_size)

    def index_missing(self, documents, chunk_size=None):
        """ Index documents from a `document` that are missing from index.

        To determine what documents are missing `mget` call with a list of
        document IDs from `documents` is performed. Then `document` are
        filtered to drop documents that were found.
        """
        log.info('Indexing documents of type `{}` missing from '
                 'index `{}`'.format(self.doc_type, self.index_name))
        if not documents:
            log.info('No documents to index')
            return
        response = ES.api.mget(
            index=self.index_name,
            doc_type=self.doc_type,
            fields=['_id'],
            body={'ids': [d['id'] for d in documents]},
        )
        indexed_ids = set(d['_id'] for d in response['docs'] if d.get('found'))
        documents = [d for d in documents if str(d['id']) not in indexed_ids]

        if not documents:
            log.info('No documents of type `{}` are missing from '
                     'index `{}`'.format(self.doc_type, self.index_name))
            return

        self._bulk('index', documents, chunk_size)

    def delete(self, ids):
        if not isinstance(ids, list):
            ids = [ids]

        self._bulk('delete', [{'id':_id, '_type': self.doc_type} for _id in ids])

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
            params['fields'] = fields

        data = ES.api.mget(**params)
        documents = _ESDocs()

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

        documents._nefertari_meta = dict(
            total=len(documents),
            start=_start,
            fields=fields,
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
                print query_string
            else:
                _params['body'] = {"query": {"match_all": {}}}

        if '_limit' in params:
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
        return ES.api.count(**params)['count']

    def get_collection(self, **params):
        __raise_on_empty = params.pop('__raise_on_empty', False)

        if 'body' in params:
            _params = params
        else:
            _params = self.build_search_params(params)

        if '_count' in params:
            return self.do_count(_params)

        # pop the fields before passing to search.
        # ES does not support passing names of nested structures
        _fields = _params.pop('fields', '')
        data = ES.api.search(**_params)
        documents = _ESDocs()

        for da in data['hits']['hits']:
            _d = da['fields'] if 'fields' in _params else da['_source']
            _d['_score'] = da['_score']
            documents.append(dict2obj(_d))

        documents._nefertari_meta = dict(
            total=data['hits']['total'],
            start=_params['from_'],
            fields=_fields,
            took=data['took'],
        )

        if not documents:
            msg = "'%s(%s)' resource not found" % (self.doc_type, params)
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

        data = ES.api.get_source(**params)
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
    def index_refs(cls, db_obj):
        for model_cls, documents in db_obj.get_reference_documents():
            if getattr(model_cls, '_index_enabled', False):
                cls(model_cls.__name__).index(documents)
