import asyncio
from asyncio import coroutine
from typing import Any, Coroutine, List
from unittest import mock
from unittest.mock import Mock

from asyncpg import (
    Connection,
    IdleInTransactionSessionTimeoutError,
    InterfaceError,
    connect_utils,
)

from opentelemetry.ext.asyncpg import AsyncPGInstrumentor, _execute
from opentelemetry.sdk.trace import Span
from opentelemetry.test.test_base import TestBase
from opentelemetry.trace.status import StatusCanonicalCode

if hasattr(Connection, "__execute") is False:
    _do_execute_return_value = (
        (None, bytes(), None),
        None,
    )  # asyncpg >= 0.13.0
else:
    _do_execute_return_value = (None, bytes(), None)  # asyncpg < 0.13.0


def _await(coro: Coroutine):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


def _coroutine_mock(return_value: Any = None, raise_exception: Any = None):
    coro = Mock(name="CoroutineResult")
    coro.return_value = return_value
    coro.side_effect = raise_exception
    coroutine_function = Mock(
        name="CoroutineFunction", side_effect=coroutine(coro)
    )
    coroutine_function.coro = coro
    return coroutine_function


def _get_connection() -> Connection:
    class ProtocolSettings:
        def __init__(self):
            self.server_version = "1"

    class Protocol:
        def __init__(self):
            self.is_connected = lambda *args, **kwargs: True

        @staticmethod
        def get_settings():
            return ProtocolSettings()

        @staticmethod
        def _get_timeout(*_, **__):
            return object()

        @property
        def is_in_transaction(self, *_, **__):
            return lambda *_, **__: False

        @staticmethod
        async def query(*_, **__):
            return None, None, None

    return Connection(
        protocol=Protocol(),
        transport=object(),
        addr="addr",
        config=connect_utils._ClientConfiguration(  # pylint: disable=W0212
            statement_cache_size=1,
            max_cached_statement_lifetime=1,
            command_timeout=1,
            max_cacheable_statement_size=1,
        ),
        loop=asyncio.get_event_loop(),
        params=None,
    )


class ConnectionParamsMock:
    def __init__(self, database: str, user: str):
        self.database = database
        self.user = user


class ConnectionMock:
    def __init__(self, params: ConnectionParamsMock):
        self._params = params


class TestAsyncPGWrapper(TestBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        AsyncPGInstrumentor().instrument(tracer_provider=cls.tracer_provider)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        AsyncPGInstrumentor().uninstrument()

    def test_wrapper_success_execution(self):
        async def _method(*_, **__):
            return "foobar"

        wrapped = _execute(_method, self.tracer_provider)
        result = _await(wrapped())
        spans: List[Span] = self.memory_exporter.get_finished_spans()
        self.assertEqual(1, len(spans))
        self.assertEqual("foobar", result)
        self.assertEqual(
            StatusCanonicalCode.OK, spans[0].status.canonical_code
        )

    def test_wrapper_exception_execution(self):
        async def _exception_method(*_, **__):
            raise Exception()

        wrapped = _execute(_exception_method, self.tracer_provider)

        with self.assertRaises(Exception):
            _await(wrapped())
        spans: List[Span] = self.memory_exporter.get_finished_spans()
        self.assertEqual(1, len(spans))
        self.assertEqual(
            StatusCanonicalCode.UNKNOWN, spans[0].status.canonical_code
        )

    def test_wrapper_interface_error_exception_execution(self):
        async def _interface_error_method(*_, **__):
            raise InterfaceError("foobar")

        wrapped = _execute(_interface_error_method, self.tracer_provider)

        with self.assertRaises(InterfaceError):
            _await(wrapped())
        spans: List[Span] = self.memory_exporter.get_finished_spans()
        self.assertEqual(
            StatusCanonicalCode.INVALID_ARGUMENT,
            spans[0].status.canonical_code,
        )

    def test_wrapper_timeout_error_exception_execution(self):
        async def _timeout_error_method(*_, **__):
            raise IdleInTransactionSessionTimeoutError()

        wrapped = _execute(_timeout_error_method, self.tracer_provider)

        with self.assertRaises(IdleInTransactionSessionTimeoutError):
            _await(wrapped())
        spans: List[Span] = self.memory_exporter.get_finished_spans()
        self.assertEqual(
            StatusCanonicalCode.DEADLINE_EXCEEDED,
            spans[0].status.canonical_code,
        )

    def test_attributes_hydration_span_without_arguments(self):
        async def _method(*_, **__):
            pass

        wrapped = _execute(_method, self.tracer_provider)
        _await(wrapped())
        spans: List[Span] = self.memory_exporter.get_finished_spans()
        self.assertEqual(spans[0].attributes, {"db.type": "sql"})

    def test_attributes_hydration_span_with_connection_argument(self):
        async def _method(*_, **__):
            pass

        wrapped = _execute(_method, self.tracer_provider)
        _await(
            wrapped(
                ConnectionMock(
                    params=ConnectionParamsMock(
                        database="database", user="user"
                    )
                )
            )
        )
        spans: List[Span] = self.memory_exporter.get_finished_spans()
        self.assertEqual(
            spans[0].attributes,
            {"db.type": "sql", "db.instance": "database", "db.user": "user"},
        )

    def test_attributes_hydration_span_with_query_argument(self):
        async def _method(*_, **__):
            pass

        wrapped = _execute(_method, self.tracer_provider)
        _await(wrapped(None, "SELECT 42;"))
        spans: List[Span] = self.memory_exporter.get_finished_spans()
        self.assertEqual(
            spans[0].attributes,
            {"db.type": "sql", "db.statement": "SELECT 42;"},
        )

    def test_attributes_hydration_span_with_parameters_argument(self):
        async def _method(*_, **__):
            pass

        wrapped = _execute(_method, self.tracer_provider)
        _await(wrapped(None, None, (1, 2, 3)))
        spans: List[Span] = self.memory_exporter.get_finished_spans()
        self.assertEqual(
            spans[0].attributes,
            {"db.type": "sql", "db.statement.parameters": (1, 2, 3)},
        )


class TestAsyncPGInstrumentation(TestBase):
    @mock.patch(
        "asyncpg.Connection._do_execute",
        new_callable=_coroutine_mock,
        return_value=_do_execute_return_value,
    )
    def test_instrumented_connection(self, *_, **__):
        AsyncPGInstrumentor().instrument()
        connection = _get_connection()
        _await(connection.execute("SELECT 42;", 1, 2, 3))
        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)
        self.assertEqual(
            spans[0].attributes,
            {
                "db.type": "sql",
                "db.statement.parameters": (1, 2, 3),
                "db.statement": "SELECT 42;",
            },
        )

    @mock.patch(
        "asyncpg.Connection._do_execute",
        new_callable=_coroutine_mock,
        return_value=_do_execute_return_value,
    )
    def test_uninstrumented_connection(self, *_, **__):
        AsyncPGInstrumentor().uninstrument()
        self.memory_exporter.clear()
        connection = _get_connection()
        _await(connection.execute("SELECT 42;", 1, 2, 3))
        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 0)

    def test_instrumentation_flags(self):
        AsyncPGInstrumentor().instrument()
        for method_name in ["_execute", "_executemany"]:
            method = getattr(Connection, method_name, None)
            self.assertTrue(
                hasattr(method, "_opentelemetry_ext_asyncpg_applied")
            )
        AsyncPGInstrumentor().uninstrument()
        for method_name in ["_execute", "_executemany"]:
            method = getattr(Connection, method_name, None)
            self.assertFalse(
                hasattr(method, "_opentelemetry_ext_asyncpg_applied")
            )

    def test_duplicated_instrumentation(self):
        AsyncPGInstrumentor().instrument()
        AsyncPGInstrumentor().instrument()
        AsyncPGInstrumentor().instrument()
        AsyncPGInstrumentor().uninstrument()
        for method_name in ["_execute", "_executemany"]:
            method = getattr(Connection, method_name, None)
            self.assertFalse(
                hasattr(method, "_opentelemetry_ext_asyncpg_applied")
            )

    def test_duplicated_uninstrumentation(self):
        AsyncPGInstrumentor().instrument()
        AsyncPGInstrumentor().uninstrument()
        AsyncPGInstrumentor().uninstrument()
        AsyncPGInstrumentor().uninstrument()
        for method_name in ["_execute", "_executemany"]:
            method = getattr(Connection, method_name, None)
            self.assertFalse(
                hasattr(method, "_opentelemetry_ext_asyncpg_applied")
            )


class TestAsyncPGConnectionMethods(TestBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        AsyncPGInstrumentor().instrument(tracer_provider=cls.tracer_provider)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        AsyncPGInstrumentor().uninstrument()

    @mock.patch(
        "asyncpg.Connection._do_execute",
        new_callable=_coroutine_mock,
        return_value=_do_execute_return_value,
    )
    def test_instrumented_execute_method(self, *_, **__):
        connection = _get_connection()
        _await(connection.execute("SELECT 42;", 1, 2, 3))
        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)
        self.assertEqual(
            spans[0].attributes,
            {
                "db.type": "sql",
                "db.statement.parameters": (1, 2, 3),
                "db.statement": "SELECT 42;",
            },
        )

    @mock.patch(
        "asyncpg.Connection._do_execute",
        new_callable=_coroutine_mock,
        return_value=_do_execute_return_value,
    )
    def test_instrumented_fetch_method(self, *_, **__):
        connection = _get_connection()
        _await(connection.fetch("SELECT 42;", 1, 2, 3))
        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)
        self.assertEqual(
            spans[0].attributes,
            {
                "db.type": "sql",
                "db.statement.parameters": (1, 2, 3),
                "db.statement": "SELECT 42;",
            },
        )

    @mock.patch(
        "asyncpg.Connection._do_execute",
        new_callable=_coroutine_mock,
        return_value=_do_execute_return_value,
    )
    def test_instrumented_executemany_method(self, *_, **__):
        connection = _get_connection()
        _await(connection.executemany("SELECT 42;", (1, 2, 3)))
        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)
        self.assertEqual(
            spans[0].attributes,
            {
                "db.type": "sql",
                "db.statement.parameters": (1, 2, 3),
                "db.statement": "SELECT 42;",
            },
        )

    @mock.patch(
        "asyncpg.Connection._do_execute",
        new_callable=_coroutine_mock,
        return_value=_do_execute_return_value,
    )
    def test_instrumented_transaction_method(self, *_, **__):
        async def _transaction_execute():
            connection = _get_connection()
            async with connection.transaction():
                await connection.execute("SELECT 42;", 1, 2, 3)

        _await(_transaction_execute())

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)
        self.assertEqual(
            spans[0].attributes,
            {
                "db.type": "sql",
                "db.statement.parameters": (1, 2, 3),
                "db.statement": "SELECT 42;",
            },
        )
