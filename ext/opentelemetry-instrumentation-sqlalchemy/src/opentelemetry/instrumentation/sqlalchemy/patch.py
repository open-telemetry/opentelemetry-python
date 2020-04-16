import sqlalchemy
import wrapt
from wrapt import wrap_function_wrapper as _w

from opentelemetry.instrumentation.sqlalchemy.engine import _wrap_create_engine


def unwrap(obj, attr):
    func = getattr(obj, attr, None)
    if (
        func
        and isinstance(func, wrapt.ObjectProxy)
        and hasattr(func, "__wrapped__")
    ):
        setattr(obj, attr, func.__wrapped__)


def patch():
    if getattr(sqlalchemy.engine, "__otel_patch", False):
        return
    setattr(sqlalchemy.engine, "__otel_patch", True)

    # patch the engine creation function
    _w("sqlalchemy", "create_engine", _wrap_create_engine)
    _w("sqlalchemy.engine", "create_engine", _wrap_create_engine)


def unpatch():
    # unpatch sqlalchemy
    if getattr(sqlalchemy.engine, "__otel_patch", False):
        setattr(sqlalchemy.engine, "__otel_patch", False)
        unwrap(sqlalchemy, "create_engine")
        unwrap(sqlalchemy.engine, "create_engine")
