# pylint: disable=redefined-outer-name, invalid-name
import pytest

from opentelemetry import trace
from opentelemetry.baggage import (
    clear,
    get_all,
    get_baggage,
    remove_baggage,
    set_baggage,
)

tracer = trace.get_tracer(__name__)


@pytest.fixture(params=[10, 100, 1000, 10000])
def baggage_size(request):
    return request.param


def set_baggage_operation(size=10):
    with tracer.start_span(name="root span"):
        ctx = get_all()
        for i in range(size):
            ctx = set_baggage(f"foo{i}", f"bar{i}", context=ctx)
    return ctx


def test_set_baggage(benchmark, baggage_size):
    ctx = benchmark(set_baggage_operation, baggage_size)
    result = get_all(ctx)
    assert len(result) == baggage_size


def test_get_baggage(benchmark, baggage_size):
    ctx = set_baggage_operation(baggage_size)

    def get_baggage_operation():
        return [get_baggage(f"foo{i}", ctx) for i in range(baggage_size)]

    result = benchmark(get_baggage_operation)
    assert result == [f"bar{i}" for i in range(baggage_size)]


def test_remove_baggage(benchmark, baggage_size):
    ctx = set_baggage_operation(baggage_size)

    def remove_operation():
        tmp_ctx = ctx
        for i in range(baggage_size):
            tmp_ctx = remove_baggage(f"foo{i}", tmp_ctx)
        return tmp_ctx

    cleared_context = benchmark(remove_operation)
    result = get_all(cleared_context)
    # After removing all baggage items, it should be empty.
    assert len(result) == 0


def test_clear_baggage(benchmark, baggage_size):
    ctx = set_baggage_operation(baggage_size)

    def clear_operation():
        return clear(ctx)

    cleared_context = benchmark(clear_operation)
    result = get_all(cleared_context)
    # After clearing the baggage should be empty.
    assert len(result) == 0
