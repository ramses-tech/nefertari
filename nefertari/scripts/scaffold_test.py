""" Reworked version of Pyramid scaffold "tests" module.

https://github.com/Pylons/pyramid/blob/master/pyramid/scaffolds/tests.py
"""
import sys
import os
import shutil
import tempfile
from subprocess import check_call, Popen, PIPE
from argparse import ArgumentParser

import pytest

# SQLA engine code when creating an app from scaffold
SQLA_ENGINE_CODE = '1'
MONGO_ENGINE_CODE = '2'
ENGINE = MONGO_ENGINE_CODE


class ScaffoldTestCommand(object):
    def make_venv(self, directory):  # pragma: no cover
        import virtualenv
        from virtualenv import Logger
        logger = Logger([(Logger.level_for_integer(2), sys.stdout)])
        virtualenv.logger = logger
        virtualenv.create_environment(directory,
                                      site_packages=False,
                                      clear=False,
                                      unzip_setuptools=True)

    def run_tests(self, scaff_name):  # pragma: no cover
        # TODO: How to pass engine number to scaffold creation?
        proj_name = scaff_name.title()
        try:
            self.old_cwd = os.getcwd()
            self.directory = tempfile.mkdtemp()
            self.make_venv(self.directory)
            py_bin = os.path.join(self.directory, 'bin', 'python')

            # Install library in created env
            here = os.path.abspath(os.path.dirname(__file__))
            os.chdir(os.path.dirname(os.path.dirname(here)))
            check_call([py_bin, 'setup.py', 'develop'])
            os.chdir(self.directory)

            # Create app from scaffold and install it
            popen = Popen(
                ['bin/pcreate', '-s', scaff_name, proj_name],
                stdin=PIPE, stdout=PIPE)
            popen.communicate(ENGINE)
            os.chdir(proj_name)
            check_call([py_bin, 'setup.py', 'install'])

            # Install test requirements
            test_reqs = os.path.join(scaff_name, 'tests', 'requirements.txt')
            if os.path.exists(test_reqs):
                pip = os.path.join(self.directory, 'bin', 'pip')
                check_call([pip, 'install', '-r', test_reqs])

            # Run actual scaffold tests
            pytest.main()
        finally:
            shutil.rmtree(self.directory)
            os.chdir(self.old_cwd)

    def parse_args(self):
        parser = ArgumentParser()
        parser.add_argument(
            '-s', '--scaffold', help='Scaffold name',
            required=True)
        self.args = parser.parse_args()

    def run(self):
        self.parse_args()
        self.run_tests(self.args.scaffold)


def main(*args, **kwargs):
    ScaffoldTestCommand().run()
