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

    add_sub = config.add_subscriber
    for evt in subscribe_to:
        add_sub(random_uuid, evt, model=AuthUserMixin, field='username')
        add_sub(lower_strip, evt, model=AuthUserMixin, field='username')
        add_sub(lower_strip, evt, model=AuthUserMixin, field='email')
        add_sub(encrypt_password, evt, model=AuthUserMixin,
                field='password')
