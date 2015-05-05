import logging

import pytest
from mock import Mock, patch, call
from elasticsearch.exceptions import TransportError

from nefertari import elasticsearch as es
from nefertari.json_httpexceptions import JHTTPBadRequest
from nefertari.utils import dictset


class TestESHttpConnection(object):

    @patch('nefertari.elasticsearch.log')
    def test_perform_request_debug(self, mock_log):
        mock_log.level = logging.DEBUG
        conn = es.ESHttpConnection()
        conn.pool = Mock()
        conn.pool.urlopen.return_value = Mock(data='foo', status=200)
        conn.perform_request('POST', 'http://localhost:9200')
        mock_log.debug.assert_called_once_with(
            "('POST', 'http://localhost:9200')")
        conn.perform_request('POST', 'http://localhost:9200'*200)
        assert mock_log.debug.call_count == 2

    def test_perform_request_exception(self):
        conn = es.ESHttpConnection()
        conn.pool = Mock()
        conn.pool.urlopen.side_effect = TransportError('N/A', '')
        with pytest.raises(JHTTPBadRequest):
            conn.perform_request('POST', 'http://localhost:9200')


class TestHelperFunctions(object):
    @patch('nefertari.elasticsearch.ES')
    def test_includeme(self, mock_es):
        config = Mock()
        config.registry.settings = {'foo': 'bar'}
        es.includeme(config)
        mock_es.setup.assert_called_once_with({'foo': 'bar'})

    def test_apply_sort(self):
        assert es.apply_sort('+foo,-bar ,zoo') == 'foo:asc,bar:desc,zoo:asc'

    def test_apply_sort_empty(self):
        assert es.apply_sort('') == ''

    def test_build_terms(self):
        terms = es.build_terms('foo', [1, 2, 3])
        assert terms == 'foo:1 OR foo:2 OR foo:3'

    def test_build_terms_custom_operator(self):
        terms = es.build_terms('foo', [1, 2, 3], operator='AND')
        assert terms == 'foo:1 AND foo:2 AND foo:3'

    def test_build_qs(self):
        qs = es.build_qs(dictset({'foo': 1, 'bar': '_all', 'zoo': 2}))
        assert qs == 'foo:1 AND zoo:2'

    def test_build_list(self):
        qs = es.build_qs(dictset({'foo': [1, 2], 'zoo': 3}))
        assert qs == 'foo:1 OR foo:2 AND zoo:3'

    def test_build_dunder_key(self):
        qs = es.build_qs(dictset({'foo': [1, 2], '__zoo__': 3}))
        assert qs == 'foo:1 OR foo:2'

    def test_build_raw_terms(self):
        qs = es.build_qs(dictset({'foo': [1, 2]}), _raw_terms=' AND qoo:1')
        assert qs == 'foo:1 OR foo:2 AND qoo:1'

    def test_build_operator(self):
        qs = es.build_qs(dictset({'foo': 1, 'qoo': 2}), operator='OR')
        assert qs == 'qoo:2 OR foo:1'

    def test_es_docs(self):
        assert issubclass(es._ESDocs, list)
        docs = es._ESDocs()
        assert docs._total == 0
        assert docs._start == 0


class TestES(object):

    @patch('nefertari.elasticsearch.ES.settings')
    def test_init(self, mock_set):
        obj = es.ES(source='Foo')
        assert obj.index_name == mock_set.index_name
        assert obj.doc_type == 'foo'
        assert obj.chunk_size == 100
        obj = es.ES(source='Foo', index_name='a', chunk_size=2)
        assert obj.index_name == 'a'
        assert obj.doc_type == 'foo'
        assert obj.chunk_size == 2

    def test_src2type(self):
        assert es.ES.src2type('FooO') == 'fooo'

    @patch('nefertari.elasticsearch.engine')
    @patch('nefertari.elasticsearch.elasticsearch')
    def test_setup(self, mock_es, mock_engine):
        settings = dictset({
            'elasticsearch.hosts': '127.0.0.1:8080,127.0.0.2:8090',
            'elasticsearch.sniff': 'true',
        })
        es.ES.setup(settings)
        mock_es.Elasticsearch.assert_called_once_with(
            hosts=[{'host': '127.0.0.1', 'port': '8080'},
                   {'host': '127.0.0.2', 'port': '8090'}],
            serializer=mock_engine.ESJSONSerializer(),
            connection_class=es.ESHttpConnection,
            sniff_on_start=True,
            sniff_on_connection_fail=True
        )
        assert es.ES.api == mock_es.Elasticsearch()

    @patch('nefertari.elasticsearch.engine')
    @patch('nefertari.elasticsearch.elasticsearch')
    def test_setup_no_settings(self, mock_es, mock_engine):
        settings = dictset({})
        with pytest.raises(Exception) as ex:
            es.ES.setup(settings)
        assert 'Bad or missing settings for elasticsearch' in str(ex.value)
        assert not mock_es.Elasticsearch.called

    def test_process_chunks(self):
        obj = es.ES('Foo', 'foondex')
        operation = Mock()
        documents = [1, 2, 3, 4, 5]
        obj.process_chunks(documents, operation, chunk_size=100)
        operation.assert_called_once_with([1, 2, 3, 4, 5])

    def test_process_chunks_multiple(self):
        obj = es.ES('Foo', 'foondex')
        operation = Mock()
        documents = [1, 2, 3, 4, 5]
        obj.process_chunks(documents, operation, chunk_size=3)
        operation.assert_has_calls([call([1, 2, 3]), call([4, 5])])

    def test_process_chunks_no_docs(self):
        obj = es.ES('Foo', 'foondex')
        operation = Mock()
        obj.process_chunks([], operation, chunk_size=3)
        assert not operation.called

    def test_prep_bulk_documents_not_dict(self):
        obj = es.ES('Foo', 'foondex')
        with pytest.raises(ValueError) as ex:
            obj.prep_bulk_documents('', 'q')
        assert str(ex.value) == 'Document type must be `dict` not a `str`'

    def test_prep_bulk_documents(self):
        obj = es.ES('Foo', 'foondex')
        docs = [
            {'_type': 'Story', 'id': 'story1'},
            {'_type': 'Story', 'id': 'story2'},
        ]
        prepared = obj.prep_bulk_documents('myaction', docs)
        assert len(prepared) == 2
        doc1meta, doc1 = prepared[0]
        assert doc1meta.keys() == ['myaction']
        assert doc1meta['myaction'].keys() == [
            'action', '_type', '_id', '_index']
        assert doc1 == {'_type': 'Story', 'id': 'story1'}
        assert doc1meta['myaction']['action'] == 'myaction'
        assert doc1meta['myaction']['_index'] == 'foondex'
        assert doc1meta['myaction']['_type'] == 'story'
        assert doc1meta['myaction']['_id'] == 'story1'

    def test_prep_bulk_documents_no_type(self):
        obj = es.ES('Foo', 'foondex')
        docs = [
            {'id': 'story2'},
        ]
        prepared = obj.prep_bulk_documents('myaction', docs)
        assert len(prepared) == 1
        doc2meta, doc2 = prepared[0]
        assert doc2meta.keys() == ['myaction']
        assert doc2meta['myaction'].keys() == [
            'action', '_type', '_id', '_index']
        assert doc2 == {'id': 'story2'}
        assert doc2meta['myaction']['action'] == 'myaction'
        assert doc2meta['myaction']['_index'] == 'foondex'
        assert doc2meta['myaction']['_type'] == 'foo'
        assert doc2meta['myaction']['_id'] == 'story2'

    def test_bulk_no_docs(self):
        obj = es.ES('Foo', 'foondex')
        assert obj._bulk('myaction', []) is None

    @patch('nefertari.elasticsearch.ES.prep_bulk_documents')
    @patch('nefertari.elasticsearch.ES.process_chunks')
    def test_bulk(self, mock_proc, mock_prep):
        obj = es.ES('Foo', 'foondex', chunk_size=1)
        docs = [
            [{'delete': {'action': 'delete', '_id': 'story1'}},
             {'_type': 'Story', 'id': 'story1', 'timestamp': 1}],
            [{'index': {'action': 'index', '_id': 'story2'}},
             {'_type': 'Story', 'id': 'story2', 'timestamp': 2}],
        ]
        mock_prep.return_value = docs
        obj._bulk('myaction', docs)
        mock_prep.assert_called_once_with('myaction', docs)
        mock_proc.assert_called_once_with(
            documents=[
                {'delete': {'action': 'delete', '_id': 'story1'}},
                {'index': {'action': 'index', '_id': 'story2'}, '_timestamp': 2},
                {'_type': 'Story', 'id': 'story2', 'timestamp': 2},
            ],
            operation=es._bulk_body,
            chunk_size=2
        )

    @patch('nefertari.elasticsearch.ES.prep_bulk_documents')
    @patch('nefertari.elasticsearch.ES.process_chunks')
    def test_bulk_no_prepared_docs(self, mock_proc, mock_prep):
        obj = es.ES('Foo', 'foondex', chunk_size=1)
        mock_prep.return_value = []
        obj._bulk('myaction', ['a'], chunk_size=4)
        mock_prep.assert_called_once_with('myaction', ['a'])
        assert not mock_proc.called

    @patch('nefertari.elasticsearch.ES._bulk')
    def test_index(self, mock_bulk):
        obj = es.ES('Foo', 'foondex')
        obj.index(['a'], chunk_size=4)
        mock_bulk.assert_called_once_with('index', ['a'], 4)

    @patch('nefertari.elasticsearch.ES._bulk')
    def test_delete(self, mock_bulk):
        obj = es.ES('Foo', 'foondex')
        obj.delete(ids=[1, 2])
        mock_bulk.assert_called_once_with(
            'delete', [{'id': 1, '_type': 'foo'}, {'id': 2, '_type': 'foo'}])

    @patch('nefertari.elasticsearch.ES._bulk')
    def test_delete_single_obj(self, mock_bulk):
        obj = es.ES('Foo', 'foondex')
        obj.delete(ids=1)
        mock_bulk.assert_called_once_with(
            'delete', [{'id': 1, '_type': 'foo'}])
