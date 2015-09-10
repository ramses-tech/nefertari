"""
Extend global scope with engine-specific variables/objects.

Usage
-----

  0. Provide 'nefertari.engine' setting in your .ini
  1. Include 'nefertari.engine' in your app's root 'includeme' as soon after
    `Configurator` setup as possible and BEFORE importing anything from
    nefertari.engine
  <- At this point you may import from nefertari.engine ->
  2. Include your models
  3. Perform database schema, engine, etc setup. Or use
    `nefertari.engine.setup_database`.

Notes
-----

Db setup should be performed after loading models, as some engines require
model schemas to be defined before creating the database. If your database
does not have the above requirement, it's up to you to decide when to set up
the db.

The specified engine module is also `config.include`d here, thus running the
engine's `includeme` function and allowing setting up required state,
performing some actions, etc.

The engine specified may be either a module or a package.
In case you build a custom engine, variables you expect to use from it
should be importable from the package itself.
E.g. ``from your.package import BaseDocument``

nefertari relies on 'nefertari.engine' being included when configuring the app.
"""
import sys
from zope.dottedname.resolve import resolve
from pyramid.settings import aslist


def includeme(config):
    engine_paths = aslist(config.registry.settings['nefertari.engine'])
    for path in engine_paths:
        config.include(path)
    _load_engines(config)
    main_engine_module = engines[0]
    _import_public_names(main_engine_module)


# replaced by registered engine modules during configuration
engines = ()


def _load_engines(config):
    global engines
    engine_paths = aslist(config.registry.settings['nefertari.engine'])
    engines = tuple([resolve(path) for path in engine_paths])


def _import_public_names(module):
    "Import public names from module into this module, like import *"
    self = sys.modules[__name__]
    for name in module.__all__:
        if hasattr(self, name):
            # don't overwrite existing names
            continue
        setattr(self, name, getattr(module, name))
