import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
CHANGES = open(os.path.join(here, 'CHANGES')).read()
VERSION = open(os.path.join(here, 'VERSION')).read()

install_requires = [
    'pyramid',
    'tempita',
    'requests',
    'simplejson',
    'elasticsearch',
    'blinker',
    'mongoengine',
    'psycopg2',
    'sqlalchemy',
    'sqlalchemy_utils',
    'pyramid_sqlalchemy',
    'zope.dottedname',
    'python-dateutil',
    'pyramid_tm'
]

setup(
    name='nefertari',
    version=VERSION,
    description='nefertari',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    author='',
    author_email='',
    url='',
    keywords='web wsgi bfg pylons pyramid rest',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    test_suite='nefertari',
    install_requires=install_requires,
)
