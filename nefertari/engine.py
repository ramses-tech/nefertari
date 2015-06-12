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
engine's `icludeme` function and allowing setting up required state,
performing some actions, etc.

The engine specified may be either a module or a package.
In case you build a custom engine, variables you expect to use from it
should be importable from the package itself.
E.g. ``from your.package import BaseDocument``

nefertari relies on 'nefertari.engine' being included when configuring the app.
"""

from zope.dottedname.resolve import resolve


def includeme(config):
    def _valid_global(g):
        ignored = ('log', 'includeme')
        return (not g.startswith('__') and g not in ignored)

    engine_path = config.registry.settings['nefertari.engine']
    config.include(engine_path)
    engine_module = resolve(engine_path)
    engine_globals = {k: v for k, v in engine_module.__dict__.items()
                      if _valid_global(k)}
    globals().update(engine_globals)
