from importlib import reload
import sys
import os

from opentelemetry import backend
from opentelemetry.trace import Tracer

class DummyTracer(Tracer):
    pass

dummy_tracer = None

def get_opentelemetry_backend_impl(type_):
    global dummy_tracer
    assert type_ is Tracer
    dummy_tracer = DummyTracer()
    return dummy_tracer

#pylint:disable=redefined-outer-name

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

def test_get_envvar(monkeypatch, backend=backend):
    global dummy_tracer

    backend = reload(backend)
    assert not sys.flags.ignore_environment # Test is not runnable with this!
    monkeypatch.setenv('OPENTELEMETRY_PYTHON_BACKEND_TRACER', __name__)
    try:
        tracer = backend.tracer()
        assert tracer is dummy_tracer
    finally:
        dummy_tracer = None
    assert type(tracer) is DummyTracer
