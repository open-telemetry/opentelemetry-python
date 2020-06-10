import functools

from asyncpg import Connection, connect_utils
from asyncpg import exceptions
from opentelemetry import trace
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import SpanKind
from opentelemetry.trace.status import StatusCanonicalCode, Status

_OPENTELEMETRY_EXT_ASYNCPG_APPLIED = "_opentelemetry_ext_asyncpg_applied"


def _exception_to_canonical_code(exc: Exception) -> StatusCanonicalCode:
    if isinstance(
            exc,
            (exceptions.InterfaceError,),
    ):
        return StatusCanonicalCode.INVALID_ARGUMENT
    if isinstance(exc, exceptions.IdleInTransactionSessionTimeoutError):
        return StatusCanonicalCode.DEADLINE_EXCEEDED
    return StatusCanonicalCode.UNKNOWN


def _hydrate_span_from_args(span, *args, **__):
    span.set_attribute("db.type", "sql")

    if len(args) <= 0:
        return span

    connection: Connection = args[0]
    if connection is not None and isinstance(connection, Connection):
        params: connect_utils._ConnectionParameters = getattr(connection, "_params", None)
        if params is not None and isinstance(params, connect_utils._ConnectionParameters):
            database_name = params.database
            database_user = params.user

            span.set_attribute("db.user", database_user)
            span.set_attribute("db.instance	", database_name)

    if len(args) > 0 and args[1] is not None:
        span.set_attribute("db.statement", args[1])

    if len(args) > 1 and args[2] is not None and len(args[2]) > 0:
        span.set_attribute("db.statement.parameters", args[2])

    return span


def _execute(wrapped, tracer_provider):
    tracer = trace.get_tracer(__name__, "0.8", tracer_provider)

    @functools.wraps(wrapped)
    async def _method(*args, **kwargs):

        exception = None

        with tracer.start_as_current_span("postgresql", kind=SpanKind.CLIENT) as span:

            span = _hydrate_span_from_args(span, *args, **kwargs)

            try:
                result = await wrapped(*args, **kwargs)
            except Exception as exc:
                exception = exc

            if exception is not None:
                span.set_status(Status(_exception_to_canonical_code(exception)))
            else:
                span.set_status(Status(StatusCanonicalCode.OK))

        if exception is not None:
            raise exception.with_traceback(exception.__traceback__)

        return result

    setattr(_method, _OPENTELEMETRY_EXT_ASYNCPG_APPLIED, True)
    return _method


class AsyncPGInstrumentor(BaseInstrumentor):

    def instrument(self, **kwargs):
        self._instrument(**kwargs)

    def uninstrument(self, **kwargs):
        self._uninstrument(**kwargs)

    @staticmethod
    def _instrument(**kwargs):
        tracer_provider = kwargs.get("tracer_provider")

        _original_execute = Connection._execute
        _original_executemany = Connection._executemany

        Connection._execute = _execute(_original_execute, tracer_provider)
        Connection._executemany = _execute(_original_executemany, tracer_provider)

    @staticmethod
    def _uninstrument(**__):
        if getattr(Connection._execute, _OPENTELEMETRY_EXT_ASYNCPG_APPLIED, False):
            original = Connection._execute.__wrapped__  # pylint:disable=no-member
            Connection._execute = original

        if getattr(Connection._executemany, _OPENTELEMETRY_EXT_ASYNCPG_APPLIED, False):
            original = Connection._executemany.__wrapped__  # pylint:disable=no-member
            Connection._executemany = original
