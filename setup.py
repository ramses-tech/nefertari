import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
VERSION = open(os.path.join(here, 'VERSION')).read()

install_requires = [
    'pyramid',
    'tempita',
    'requests',
    'simplejson',
    'elasticsearch',
    'blinker',
    'zope.dottedname',
    'cryptacular',
    'six',
]

setup(
    name='nefertari',
    version=VERSION,
    description='REST API framework for Pyramid',
    long_description=README,
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    author='Ramses',
    author_email='hello@ramses.tech',
    url='https://github.com/ramses-tech/nefertari',
    keywords='web wsgi bfg pylons pyramid rest api elasticsearch',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    test_suite='nefertari',
    install_requires=install_requires,
    entry_points="""\
    [console_scripts]
        nefertari.index = nefertari.scripts.es:main
        nefertari.post2api = nefertari.scripts.post2api:main
    [pyramid.scaffold]
        nefertari_starter = nefertari.scaffolds:NefertariStarterTemplate
    """,
)
