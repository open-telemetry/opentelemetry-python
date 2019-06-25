from importlib import reload
import sys

import pytest

from opentelemetry import backend
from opentelemetry.trace import Tracer

class DummyTracer(Tracer):
    pass

DUMMY_TRACER = None

def get_opentelemetry_backend_impl(type_):
    global DUMMY_TRACER #pylint:disable=global-statement
    assert type_ is Tracer
    DUMMY_TRACER = DummyTracer()
    return DUMMY_TRACER

#pylint:disable=redefined-outer-name,protected-access,unidiomatic-typecheck

def test_get_default(backend=backend):
    backend = reload(backend)
    backend._UNIT_TEST_IGNORE_ENV = True
    tracer = backend.tracer()
    assert type(tracer) is Tracer

def test_get_set(backend=backend):
    backend = reload(backend)
    set_tracer = DummyTracer()
    backend.set_tracer(set_tracer)
    tracer = backend.tracer()
    assert tracer is set_tracer

    # Set again
    set_tracer = DummyTracer()
    backend.set_tracer(set_tracer)
    tracer = backend.tracer()
    assert tracer is set_tracer

def test_get_set_import_from(backend=backend):
    backend = reload(backend)
    get_tracer = backend.tracer # Simulate `import tracer from backend as get_tracer`
    set_tracer = DummyTracer()
    backend.set_tracer(set_tracer)
    tracer = get_tracer()
    assert tracer is set_tracer

    # Set again
    set_tracer = DummyTracer()
    backend.set_tracer(set_tracer)
    tracer = get_tracer()
    assert tracer is set_tracer

@pytest.mark.parametrize('envvar_suffix', ['TRACER', 'DEFAULT'])
def test_get_envvar(envvar_suffix, monkeypatch, backend=backend):
    global DUMMY_TRACER #pylint:disable=global-statement

    backend = reload(backend)
    assert not sys.flags.ignore_environment # Test is not runnable with this!
    monkeypatch.setenv('OPENTELEMETRY_PYTHON_BACKEND_' + envvar_suffix, __name__)
    try:
        tracer = backend.tracer()
        assert tracer is DUMMY_TRACER
    finally:
        DUMMY_TRACER = None
    assert type(tracer) is DummyTracer
