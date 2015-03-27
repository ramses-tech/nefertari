from argparse import ArgumentParser
import sys
import textwrap
import urlparse
import logging

from pyramid.paster import bootstrap
from zope.dottedname.resolve import resolve

from nefertari.elasticsearch import ES
from nefertari.utils import dictset, split_strip, to_dicts


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
            '--quiet', help='quiet mode', action='store_true',
            default=False)
        parser.add_argument(
            '--models', help='list of dotted paths of models to index',
            required=True)
        parser.add_argument(
            '--params', help='url encoded params for each model')
        parser.add_argument('--index', help='index name', default=None)
        parser.add_argument('--bulk', help='index bulk size', type=int)

        self.options = parser.parse_args()
        if not self.options.config:
            return parser.print_help()

        env = self.bootstrap[0](self.options.config)
        registry = env['registry']

        self.log = log

        if not self.options.quiet:
            self.log.setLevel(logging.INFO)

        self.settings = dictset(registry.settings)

    def run(self, quiet=False):
        ES.setup(self.settings)
        models_paths = split_strip(self.options.models)

        for path in models_paths:
            model = resolve(path)
            model_name = path.split('.')[-1]

            params = self.options.params or ''
            params = dict([
                [k, v[0]] for k, v in urlparse.parse_qs(params).items()
            ])
            params.setdefault('_limit', params.get('_limit', 10000))
            bulk_size = self.options.bulk or params['_limit']

            es = ES(source=model_name, index_name=self.options.index)
            query_set = model.get_collection(**params)
            query_set = to_dicts(query_set)
            count = len(query_set)

            start = end = 0
            while count:
                if count < bulk_size:
                    bulk_size = count
                end += bulk_size

                es.index(query_set[start:end])

                start += bulk_size
                count -= bulk_size

        return 0
