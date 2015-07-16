import pytest


@pytest.fixture(scope='module')
def engine_mock(request):
    import nefertari
    from mock import Mock

    original_engine = nefertari.engine
    nefertari.engine = Mock()
    nefertari.engine.BaseDocument = object

    def clear():
        nefertari.engine = original_engine
    request.addfinalizer(clear)

    return nefertari.engine
