from argparse import ArgumentParser
import sys
import logging

from pyramid.paster import bootstrap
from pyramid.config import Configurator
from six.moves import urllib

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
            '--params', help='Url-encoded params for each model')
        parser.add_argument('--index', help='Index name', default=None)
        parser.add_argument(
            '--chunk',
            help=('Index chunk size. If chunk size not provided '
                  '`elasticsearch.chunk_size` setting is used'),
            type=int)

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--models',
            help=('Comma-separated list of model names to index'))
        group.add_argument(
            '--recreate',
            help='Recreate index and reindex all documents',
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

    def index_models(self, model_names):
        self.log.info('Indexing models documents')
        params = self.options.params or ''
        params = dict([
            [k, v[0]] for k, v in urllib.parse.parse_qs(params).items()
        ])
        params.setdefault('_limit', params.get('_limit', 10000))
        chunk_size = self.options.chunk or params['_limit']

        for model_name in model_names:
            self.log.info('Processing model `{}`'.format(model_name))
            model = engine.get_document_cls(model_name)
            es = ES(source=model_name, index_name=self.options.index,
                    chunk_size=chunk_size)
            query_set = model.get_collection(**params)
            documents = to_dicts(query_set)
            self.log.info('Indexing missing `{}` documents'.format(
                model_name))
            es.index_missing_documents(documents)

    def recreate_index(self):
        self.log.info('Deleting index')
        ES.delete_index()
        self.log.info('Creating index')
        ES.create_index()
        self.log.info('Creating mappings')
        ES.setup_mappings()

    def run(self):
        ES.setup(self.settings)
        if self.options.recreate:
            self.recreate_index()
            models = engine.get_document_classes()
            model_names = [
                name for name, model in models.items()
                if getattr(model, '_index_enabled', False)]
        else:
            model_names = split_strip(self.options.models)
        self.index_models(model_names)
