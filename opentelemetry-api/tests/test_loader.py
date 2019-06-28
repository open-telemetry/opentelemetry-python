from importlib import reload
import sys

import pytest

from opentelemetry import loader
from opentelemetry import trace

DUMMY_TRACER = None

class DummyTracer(trace.Tracer):
    pass

@pytest.fixture(autouse=True)
def reload_mods():
    reload(loader)
    reload(trace)

    # Need to reload self, otherwise DummyTracer will have the wrong base class
    # after reloading `trace`.
    reload(sys.modules[__name__])

def get_opentelemetry_implementation(type_):
    global DUMMY_TRACER #pylint:disable=global-statement
    assert type_ is trace.Tracer
    DUMMY_TRACER = DummyTracer()
    return DUMMY_TRACER

#pylint:disable=redefined-outer-name,protected-access,unidiomatic-typecheck

def test_get_default():
    tracer = trace.tracer()
    assert type(tracer) is trace.Tracer

def test_preferred_impl():
    trace.set_preferred_tracer_implementation(get_opentelemetry_implementation)
    tracer = trace.tracer()
    assert tracer is DUMMY_TRACER

@pytest.mark.parametrize('setter', [
    trace.set_preferred_tracer_implementation,
    loader.set_preferred_default_implementation])
def test_preferred_impl_default(setter):
    setter(get_opentelemetry_implementation)
    tracer = trace.tracer()
    assert tracer is DUMMY_TRACER

def test_try_set_again():
    assert trace.tracer()
    # Set again
    with pytest.raises(RuntimeError) as excinfo:
        trace.set_preferred_tracer_implementation(get_opentelemetry_implementation)
    assert "already loaded" in str(excinfo.value)

@pytest.mark.parametrize('envvar_suffix', ['TRACER', 'DEFAULT'])
def test_get_envvar(envvar_suffix, monkeypatch):
    global DUMMY_TRACER #pylint:disable=global-statement

    assert not sys.flags.ignore_environment # Test is not runnable with this!
    monkeypatch.setenv('OPENTELEMETRY_PYTHON_IMPLEMENTATION_' + envvar_suffix, __name__)
    try:
        tracer = trace.tracer()
        assert tracer is DUMMY_TRACER
    finally:
        DUMMY_TRACER = None
    assert type(tracer) is DummyTracer
