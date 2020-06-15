import functools
import typing

import wrapt
from aiopg.utils import _ContextManager, _PoolAcquireContextManager

from opentelemetry.trace import SpanKind, Tracer
from opentelemetry.trace.status import Status, StatusCanonicalCode


# pylint: disable=abstract-method
class AsyncProxyObject(wrapt.ObjectProxy):
    def __aiter__(self):
        return self.__wrapped__.__aiter__()

    async def __anext__(self):
        result = await self.__wrapped__.__anext__()
        return result

    async def __aenter__(self):
        return await self.__wrapped__.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return await self.__wrapped__.__aexit__(exc_type, exc_val, exc_tb)

    def __await__(self):
        return self.__wrapped__.__await__()


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

    async def wrapped_connection(
        self,
        connect_method: typing.Callable[..., typing.Any],
        args: typing.Tuple[typing.Any, typing.Any],
        kwargs: typing.Dict[typing.Any, typing.Any],
    ):
        """Add object proxy to connection object.
        """
        connection = await connect_method(*args, **kwargs)
        # pylint: disable=protected-access
        self.get_connection_attributes(connection._conn)
        return get_traced_connection_proxy(connection, self)

    async def wrapped_pool(self, create_pool_method, args, kwargs):
        pool = await create_pool_method(*args, **kwargs)
        async with pool.acquire() as connection:
            # pylint: disable=protected-access
            self.get_connection_attributes(connection._conn)
        return get_traced_pool_proxy(pool, self)

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
    class TracedConnectionProxy(AsyncProxyObject):
        # pylint: disable=unused-argument
        def __init__(self, connection, *args, **kwargs):
            super().__init__(connection)

        def cursor(self, *args, **kwargs):
            coro = self._cursor(*args, **kwargs)
            return _ContextManager(coro)

        async def _cursor(self, *args, **kwargs):
            # pylint: disable=protected-access
            cursor = await self.__wrapped__._cursor(*args, **kwargs)
            return get_traced_cursor_proxy(cursor, db_api_integration)

    return TracedConnectionProxy(connection, *args, **kwargs)


def get_traced_pool_proxy(pool, db_api_integration, *args, **kwargs):
    # pylint: disable=abstract-method
    class TracedPoolProxy(AsyncProxyObject):
        # pylint: disable=unused-argument
        def __init__(self, pool, *args, **kwargs):
            super().__init__(pool)

        def acquire(self):
            """Acquire free connection from the pool."""
            coro = self._acquire()
            return _PoolAcquireContextManager(coro, self)

        async def _acquire(self):
            # pylint: disable=protected-access
            connection = await self.__wrapped__._acquire()
            return get_traced_connection_proxy(
                connection, db_api_integration, *args, **kwargs
            )

    return TracedPoolProxy(pool, *args, **kwargs)


class AsyncTracedCursor:
    def __init__(self, db_api_integration: AiopgIntegration):
        self._db_api_integration = db_api_integration

    async def traced_execution(
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
                result = await query_method(*args, **kwargs)
                span.set_status(Status(StatusCanonicalCode.OK))
                return result
            except Exception as ex:  # pylint: disable=broad-except
                span.set_status(Status(StatusCanonicalCode.UNKNOWN, str(ex)))
                raise ex


def get_traced_cursor_proxy(cursor, db_api_integration, *args, **kwargs):
    _traced_cursor = AsyncTracedCursor(db_api_integration)

    # pylint: disable=abstract-method
    class AsyncTracedCursorProxy(AsyncProxyObject):

        # pylint: disable=unused-argument
        def __init__(self, cursor, *args, **kwargs):
            super().__init__(cursor)

        async def execute(self, *args, **kwargs):
            result = await _traced_cursor.traced_execution(
                self.__wrapped__.execute, *args, **kwargs
            )
            return result

        async def executemany(self, *args, **kwargs):
            result = await _traced_cursor.traced_execution(
                self.__wrapped__.executemany, *args, **kwargs
            )
            return result

        async def callproc(self, *args, **kwargs):
            result = await _traced_cursor.traced_execution(
                self.__wrapped__.callproc, *args, **kwargs
            )
            return result

    return AsyncTracedCursorProxy(cursor, *args, **kwargs)
