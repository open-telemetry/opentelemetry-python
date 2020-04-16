# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from sqlalchemy.event import listen

from opentelemetry import trace
from opentelemetry.instrumentation.sqlalchemy.version import __version__
from opentelemetry.trace.status import Status, StatusCanonicalCode

# Network attribute semantic convention here:
# https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/trace/semantic_conventions/span-general.md#general-network-connection-attributes
_HOST = "net.peer.name"
_PORT = "net.peer.port"
# Database semantic conventions here:
# https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/trace/semantic_conventions/database.md
_ROWS = "sql.rows"  # number of rows returned by a query
_STMT = "db.statement"
_DB = "db.type"
_URL = "db.url"


def _normalize_vendor(vendor):
    """ Return a canonical name for a type of database. """
    if not vendor:
        return "db"  # should this ever happen?

    if "sqlite" in vendor:
        return "sqlite"

    if "postgres" in vendor or vendor == "psycopg2":
        return "postgres"

    return vendor


def trace_engine(engine, tracer=None, service=None):
    """
    Add tracing instrumentation to the given sqlalchemy engine or instance.

    Args:
        engine: a SQLAlchemy engine class or instance
        tracer: a tracer instance. will default to the global
        service: the name of the service to trace.
    """
    tracer = tracer or trace.get_tracer(
        _normalize_vendor(engine.name), __version__
    )
    EngineTracer(tracer, service, engine)


# pylint: disable=unused-argument
def _wrap_create_engine(func, module, args, kwargs):
    """Trace the SQLAlchemy engine, creating an `EngineTracer`
    object that will listen to SQLAlchemy events. A PIN object
    is attached to the engine instance so that it can be
    used later.
    """
    # the service name is set to `None` so that the engine
    # name is used by default; users can update this setting
    # using the PIN object
    engine = func(*args, **kwargs)
    EngineTracer(
        trace.get_tracer(_normalize_vendor(engine.name), __version__),
        None,
        engine,
    )
    return engine


class EngineTracer:
    def __init__(self, tracer: trace.Tracer, service, engine):
        self.tracer = tracer
        self.engine = engine
        self.vendor = _normalize_vendor(engine.name)
        self.service = service or self.vendor
        self.name = "%s.query" % self.vendor
        # TODO: revisit, might be better done w/ context attach/detach
        self.current_span = None

        listen(engine, "before_cursor_execute", self._before_cur_exec)
        listen(engine, "after_cursor_execute", self._after_cur_exec)
        listen(engine, "dbapi_error", self._dbapi_error)

    # pylint: disable=unused-argument
    def _before_cur_exec(self, conn, cursor, statement, *args):
        self.current_span = self.tracer.start_span(self.name)
        with self.tracer.use_span(self.current_span, end_on_exit=False):
            self.current_span.set_attribute("service", self.vendor)
            self.current_span.set_attribute(_STMT, statement)

            if not _set_attributes_from_url(
                self.current_span, conn.engine.url
            ):
                _set_attributes_from_cursor(
                    self.current_span, self.vendor, cursor
                )

    # pylint: disable=unused-argument
    def _after_cur_exec(self, conn, cursor, statement, *args):
        if not self.current_span:
            return

        try:
            if cursor and cursor.rowcount >= 0:
                self.current_span.set_attribute(_ROWS, cursor.rowcount)
        finally:
            self.current_span.end()

    # pylint: disable=unused-argument
    def _dbapi_error(self, conn, cursor, statement, *args):
        if not self.current_span:
            return

        try:
            # span.set_traceback()
            self.current_span.set_status(
                Status(StatusCanonicalCode.UNKNOWN, str("something happened"))
            )
        finally:
            self.current_span.end()


def _set_attributes_from_url(span: trace.Span, url):
    """ set connection tags from the url. return true if successful. """
    if url.host:
        span.set_attribute(_HOST, url.host)
    if url.port:
        span.set_attribute(_PORT, url.port)
    if url.database:
        span.set_attribute(_DB, url.database)

    return hasattr(span, "attributes") and bool(
        span.attributes.get(_HOST, False)
    )


def _set_attributes_from_cursor(span: trace.Span, vendor, cursor):
    """ attempt to set db connection tags by introspecting the cursor. """
    if vendor == "postgres":
        # pylint: disable=import-outside-toplevel
        from psycopg2.extensions import parse_dsn

        if hasattr(cursor, "connection") and hasattr(cursor.connection, "dsn"):
            dsn = getattr(cursor.connection, "dsn", None)
            if dsn:
                data = parse_dsn(dsn)
                span.set_attribute(_DB, data.get("dbname"))
                span.set_attribute(_HOST, data.get("host"))
                span.set_attribute(_PORT, int(data.get("port")))
