def includeme(config):
    """ Set up event subscribers. """
    from .models import (
        AuthUserMixin,
        random_uuid,
        lower_strip,
        encrypt_password,
    )
    from nefertari import events

    subscribe_to = (
        events.before_create,
        events.before_update,
        events.before_replace,
        events.before_update_many,
    )

    add_sub = config.subscribe_to_events
    add_sub(random_uuid, subscribe_to, model=AuthUserMixin,
            field='username')
    add_sub(lower_strip, subscribe_to, model=AuthUserMixin,
            field='username')
    add_sub(lower_strip, subscribe_to, model=AuthUserMixin,
            field='email')
    add_sub(encrypt_password, subscribe_to, model=AuthUserMixin,
            field='password')
