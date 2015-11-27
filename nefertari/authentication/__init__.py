def includeme(config):
    """ Set up event subscribers. """
    from .models import (
        AuthUserMixin,
        random_uuid,
        lower_strip,
        encrypt_password,
    )
    add_proc = config.add_field_processors
    add_proc(
        [random_uuid, lower_strip],
        model=AuthUserMixin, field='username')
    add_proc([lower_strip], model=AuthUserMixin, field='email')
    add_proc([encrypt_password], model=AuthUserMixin, field='password')
