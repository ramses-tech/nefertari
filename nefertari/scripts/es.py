from argparse import ArgumentParser
import sys
import urlparse
import logging

from pyramid.paster import bootstrap
from pyramid.config import Configurator

from nefertari.utils import dictset, split_strip, to_dicts
from nefertari.elasticsearch import ES
from nefertari import engine


def main(argv=sys.argv, quiet=False):
    log = logging.getLogger()
    log.setLevel(logging.WARNING)
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
    ch.setFormatter(formatter)
    log.addHandler(ch)

    command = ESCommand(argv, log)
    return command.run()


class ESCommand(object):

    bootstrap = (bootstrap,)
    stdout = sys.stdout
    usage = '%prog config_uri <models'

    def __init__(self, argv, log):
        parser = ArgumentParser(description=__doc__)

        parser.add_argument(
            '-c', '--config', help='config.ini (required)',
            required=True)
        parser.add_argument(
            '--quiet', help='Quiet mode', action='store_true',
            default=False)
        parser.add_argument(
            '--models',
            help=('Comma-separated list of model names to index '
                  '(required)'),
            required=True)
        parser.add_argument(
            '--params', help='Url-encoded params for each model')
        parser.add_argument('--index', help='Index name', default=None)
        parser.add_argument(
            '--chunk',
            help=('Index chunk size. If chunk size not provided '
                  '`elasticsearch.chunk_size` setting is used'),
            type=int)
        parser.add_argument(
            '--force',
            help=('Recreate ES mappings and reindex all documents of provided '
                  'models. By default, only documents that are missing from '
                  'index are indexed.'),
            action='store_true',
            default=False)

        self.options = parser.parse_args()
        if not self.options.config:
            return parser.print_help()

        # Prevent ES.setup_mappings running on bootstrap;
        # Restore ES._mappings_setup after bootstrap is over
        mappings_setup = getattr(ES, '_mappings_setup', False)
        try:
            ES._mappings_setup = True
            env = self.bootstrap[0](self.options.config)
        finally:
            ES._mappings_setup = mappings_setup

        registry = env['registry']
        # Include 'nefertari.engine' to setup specific engine
        config = Configurator(settings=registry.settings)
        config.include('nefertari.engine')

        self.log = log

        if not self.options.quiet:
            self.log.setLevel(logging.INFO)

        self.settings = dictset(registry.settings)

    def run(self):
        ES.setup(self.settings)
        model_names = split_strip(self.options.models)

        for model_name in model_names:
            self.log.info('Processing model `{}`'.format(model_name))
            model = engine.get_document_cls(model_name)

            params = self.options.params or ''
            params = dict([
                [k, v[0]] for k, v in urlparse.parse_qs(params).items()
            ])
            params.setdefault('_limit', params.get('_limit', 10000))
            chunk_size = self.options.chunk or params['_limit']

            es = ES(source=model_name, index_name=self.options.index,
                    chunk_size=chunk_size)
            query_set = model.get_collection(**params)
            documents = to_dicts(query_set)

            if self.options.force:
                self.log.info('Recreating `{}` ES mapping'.format(model_name))
                es.delete_mapping()
                es.put_mapping(body=model.get_es_mapping())
                self.log.info('Indexing all `{}` documents'.format(
                    model_name))
                es.index(documents)
            else:
                self.log.info('Indexing missing `{}` documents'.format(
                    model_name))
                es.index_missing_documents(documents)

        return 0
