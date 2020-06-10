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

"""
The trace integration with aiopg based on dbapi integration, where replaced sync wrap methods to async

Usage
-----

.. code-block:: python

    from opentelemetry import trace
    from opentelemetry.ext.aiopg import trace_integration
    from opentelemetry.trace import TracerProvider

    trace.set_tracer_provider(TracerProvider())

    trace_integration(aiopg.connection, "_connect", "postgresql", "sql")

API
---
"""
import asyncio
import functools
import logging
import typing

import wrapt
from aiopg.utils import _ContextManager

from opentelemetry.ext.aiopg.version import __version__
from opentelemetry.instrumentation.utils import unwrap
from opentelemetry.trace import SpanKind, Tracer, TracerProvider, get_tracer
from opentelemetry.trace.status import Status, StatusCanonicalCode

logger = logging.getLogger(__name__)


def trace_integration(
    connect_module: typing.Callable[..., typing.Any],
    connect_method_name: str,
    database_component: str,
    database_type: str = "",
    connection_attributes: typing.Dict = None,
    tracer_provider: typing.Optional[TracerProvider] = None,
):
    """Integrate with aiopg library.
        based on dbapi integration, where replaced sync wrap methods to async

        Args:
            connect_module: Module name where connect method is available.
            connect_method_name: The connect method name.
            database_component: Database driver name or database name "postgreSQL".
            database_type: The Database type. For any SQL database, "sql".
            connection_attributes: Attribute names for database, port, host and
                user in Connection object.
            tracer_provider: The :class:`opentelemetry.trace.TracerProvider` to
                use. If ommited the current configured one is used.
    """
    tracer = get_tracer(__name__, __version__, tracer_provider)
    wrap_connect(
        tracer,
        connect_module,
        connect_method_name,
        database_component,
        database_type,
        connection_attributes,
    )


def wrap_connect(
    tracer: Tracer,
    connect_module: typing.Callable[..., typing.Any],
    connect_method_name: str,
    database_component: str,
    database_type: str = "",
    connection_attributes: typing.Dict = None,
):
    """Integrate with aiopg library.
        https://github.com/aio-libs/aiopg

        Args:
            tracer: The :class:`opentelemetry.trace.Tracer` to use.
            connect_module: Module name where connect method is available.
            connect_method_name: The connect method name.
            database_component: Database driver name or database name "postgreSQL".
            database_type: The Database type. For any SQL database, "sql".
            connection_attributes: Attribute names for database, port, host and
                user in Connection object.
    """

    # pylint: disable=unused-argument
    @asyncio.coroutine
    def wrap_connect_(
        wrapped: typing.Callable[..., typing.Any],
        instance: typing.Any,
        args: typing.Tuple[typing.Any, typing.Any],
        kwargs: typing.Dict[typing.Any, typing.Any],
    ):
        db_integration = AiopgIntegration(
            tracer,
            database_component,
            database_type=database_type,
            connection_attributes=connection_attributes,
        )
        connection = yield from db_integration.wrapped_connection(
            wrapped, args, kwargs
        )
        return connection

    try:
        wrapt.wrap_function_wrapper(
            connect_module, connect_method_name, wrap_connect_
        )
    except Exception as ex:  # pylint: disable=broad-except
        logger.warning("Failed to integrate with aiopg. %s", str(ex))


def unwrap_connect(
    connect_module: typing.Callable[..., typing.Any], connect_method_name: str,
):
    """"Disable integration with aiopg library.
        https://github.com/aio-libs/aiopg

        Args:
            connect_module: Module name where the connect method is available.
            connect_method_name: The connect method name.
    """
    unwrap(connect_module, connect_method_name)


def instrument_connection(
    tracer,
    connection,
    database_component: str,
    database_type: str = "",
    connection_attributes: typing.Dict = None,
):
    """Enable instrumentation in a database connection.

    Args:
        tracer: The :class:`opentelemetry.trace.Tracer` to use.
        connection: The connection to instrument.
        database_component: Database driver name or database name "postgreSQL".
        database_type: The Database type. For any SQL database, "sql".
        connection_attributes: Attribute names for database, port, host and
            user in a connection object.

    Returns:
        An instrumented connection.
    """
    db_integration = AiopgIntegration(
        tracer,
        database_component,
        database_type,
        connection_attributes=connection_attributes,
    )
    db_integration.get_connection_attributes(connection)
    return get_traced_connection_proxy(connection, db_integration)


def uninstrument_connection(connection):
    """Disable instrumentation in a database connection.

    Args:
        connection: The connection to uninstrument.

    Returns:
        An uninstrumented connection.
    """
    if isinstance(connection, wrapt.ObjectProxy):
        return connection.__wrapped__

    logger.warning("Connection is not instrumented")
    return connection


class AiopgIntegration:
    def __init__(
        self,
        tracer: Tracer,
        database_component: str,
        database_type: str = "sql",
        connection_attributes=None,
    ):
        self.connection_attributes = connection_attributes
        if self.connection_attributes is None:
            self.connection_attributes = {
                "database": "database",
                "port": "port",
                "host": "host",
                "user": "user",
            }
        self.tracer = tracer
        self.database_component = database_component
        self.database_type = database_type
        self.connection_props = {}
        self.span_attributes = {}
        self.name = ""
        self.database = ""

    @asyncio.coroutine
    def wrapped_connection(
        self,
        connect_method: typing.Callable[..., typing.Any],
        args: typing.Tuple[typing.Any, typing.Any],
        kwargs: typing.Dict[typing.Any, typing.Any],
    ):
        """Add object proxy to connection object.
        """
        connection = yield from connect_method(*args, **kwargs)
        self.get_connection_attributes(connection)
        return get_traced_connection_proxy(connection, self)

    def get_connection_attributes(self, connection):
        # Populate span fields using connection
        for key, value in self.connection_attributes.items():
            # Allow attributes nested in connection object
            attribute = functools.reduce(
                lambda attribute, attribute_value: getattr(
                    attribute, attribute_value, None
                ),
                value.split("."),
                connection,
            )
            if attribute:
                self.connection_props[key] = attribute
        self.name = self.database_component
        self.database = self.connection_props.get("database", "")
        if self.database:
            # PyMySQL encodes names with utf-8
            if hasattr(self.database, "decode"):
                self.database = self.database.decode(errors="ignore")
            self.name += "." + self.database
        user = self.connection_props.get("user")
        if user is not None:
            self.span_attributes["db.user"] = str(user)
        host = self.connection_props.get("host")
        if host is not None:
            self.span_attributes["net.peer.name"] = host
        port = self.connection_props.get("port")
        if port is not None:
            self.span_attributes["net.peer.port"] = port


def get_traced_connection_proxy(
    connection, db_api_integration, *args, **kwargs
):
    # pylint: disable=abstract-method
    class TracedConnectionProxy(wrapt.ObjectProxy):
        # pylint: disable=unused-argument
        def __init__(self, connection, *args, **kwargs):
            wrapt.ObjectProxy.__init__(self, connection)

        def cursor(self, *args, **kwargs):
            # unfortunately we also need to patch this method as otherwise "self"
            # ends up being the aiopg connection object
            coro = self._cursor(*args, **kwargs)
            return _ContextManager(coro)

        @asyncio.coroutine
        def _cursor(self, *args, **kwargs):
            # pylint: disable=protected-access
            cursor = yield from self.__wrapped__._cursor(*args, **kwargs)
            return get_traced_cursor_proxy(cursor, db_api_integration)

        @asyncio.coroutine
        def __aenter__(self):
            return self.__wrapped__.__aenter__()

        @asyncio.coroutine
        def __aexit__(self, exc_type, exc_val, exc_tb):
            self.__wrapped__.__aexit__(exc_type, exc_val, exc_tb)

    return TracedConnectionProxy(connection, *args, **kwargs)


class AsyncTracedCursor:
    def __init__(self, db_api_integration: AiopgIntegration):
        self._db_api_integration = db_api_integration

    @asyncio.coroutine
    def traced_execution(
        self,
        query_method: typing.Callable[..., typing.Any],
        *args: typing.Tuple[typing.Any, typing.Any],
        **kwargs: typing.Dict[typing.Any, typing.Any]
    ):

        statement = args[0] if args else ""
        with self._db_api_integration.tracer.start_as_current_span(
            self._db_api_integration.name, kind=SpanKind.CLIENT
        ) as span:
            span.set_attribute(
                "component", self._db_api_integration.database_component
            )
            span.set_attribute(
                "db.type", self._db_api_integration.database_type
            )
            span.set_attribute(
                "db.instance", self._db_api_integration.database
            )
            span.set_attribute("db.statement", statement)

            for (
                attribute_key,
                attribute_value,
            ) in self._db_api_integration.span_attributes.items():
                span.set_attribute(attribute_key, attribute_value)

            if len(args) > 1:
                span.set_attribute("db.statement.parameters", str(args[1]))

            try:
                result = yield from query_method(*args, **kwargs)
                span.set_status(Status(StatusCanonicalCode.OK))
                return result
            except Exception as ex:  # pylint: disable=broad-except
                span.set_status(Status(StatusCanonicalCode.UNKNOWN, str(ex)))
                raise ex


def get_traced_cursor_proxy(cursor, db_api_integration, *args, **kwargs):
    _traced_cursor = AsyncTracedCursor(db_api_integration)

    # pylint: disable=abstract-method
    class AsyncTracedCursorProxy(wrapt.ObjectProxy):

        # pylint: disable=unused-argument
        def __init__(self, cursor, *args, **kwargs):
            wrapt.ObjectProxy.__init__(self, cursor)

        @asyncio.coroutine
        def execute(self, *args, **kwargs):
            result = yield from _traced_cursor.traced_execution(
                self.__wrapped__.execute, *args, **kwargs
            )
            return result

        @asyncio.coroutine
        def executemany(self, *args, **kwargs):
            result = yield from _traced_cursor.traced_execution(
                self.__wrapped__.executemany, *args, **kwargs
            )
            return result

        @asyncio.coroutine
        def callproc(self, *args, **kwargs):
            result = yield from _traced_cursor.traced_execution(
                self.__wrapped__.callproc, *args, **kwargs
            )
            return result

        def __aiter__(self):
            return self.__wrapped__.__aiter__()

        @asyncio.coroutine
        def __anext__(self):
            result = yield from self.__wrapped__.__anext__()
            return result

        @asyncio.coroutine
        def __aenter__(self):
            result = yield from self.__wrapped__.__aenter__()
            return result

        @asyncio.coroutine
        def __aexit__(self, exc_type, exc_val, exc_tb):
            result = yield from self.__wrapped__.__aexit__(
                exc_type, exc_val, exc_tb
            )
            return result

    return AsyncTracedCursorProxy(cursor, *args, **kwargs)
