import opentelemetry.trace


def dummy_check_mypy_returntype() -> opentelemetry.trace.Tracer:
    return opentelemetry.trace.tracer()
