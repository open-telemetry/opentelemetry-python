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
This library allows tracing PostgreSQL queries made by the
`asyncpg <https://magicstack.github.io/asyncpg/current/>`_ library.

Usage
-----

.. code-block:: python

    import asyncpg
    import opentelemetry.ext.asyncpg

    # You can optionally pass a custom TracerProvider to AsyncPGInstrumentor.instrument()
    opentelemetry.ext.asyncpg.AsyncPGInstrumentor().instrument()
    conn = await asyncpg.connect(user='user', password='password',
                                 database='database', host='127.0.0.1')
    values = await conn.fetch('''SELECT 42;''')

API
---
"""

import functools

from asyncpg import Connection, exceptions

from opentelemetry import trace
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.trace import SpanKind
from opentelemetry.trace.status import Status, StatusCanonicalCode

_APPLIED = "_opentelemetry_ext_asyncpg_applied"


def _exception_to_canonical_code(exc: Exception) -> StatusCanonicalCode:
    if isinstance(exc, (exceptions.InterfaceError,),):
        return StatusCanonicalCode.INVALID_ARGUMENT
    if isinstance(exc, exceptions.IdleInTransactionSessionTimeoutError):
        return StatusCanonicalCode.DEADLINE_EXCEEDED
    return StatusCanonicalCode.UNKNOWN


def _hydrate_span_from_args(span, *args, **__):
    span.set_attribute("db.type", "sql")

    if len(args) <= 0:
        return span

    connection = args[0]
    if connection is not None:
        params = getattr(connection, "_params", None)
        if params is not None:
            database_name = getattr(params, "database", None)
            if database_name is not None:
                span.set_attribute("db.instance", database_name)

            database_user = getattr(params, "user", None)
            if database_user is not None:
                span.set_attribute("db.user", database_user)

    if len(args) > 1 and args[1] is not None:
        span.set_attribute("db.statement", args[1])

    if len(args) > 2 and args[2] is not None and len(args[2]) > 0:
        span.set_attribute("db.statement.parameters", args[2])

    return span


def _execute(wrapped, tracer_provider):
    tracer = trace.get_tracer(__name__, "0.8", tracer_provider)

    @functools.wraps(wrapped)
    async def _method(*args, **kwargs):

        exception = None

        with tracer.start_as_current_span(
            "postgresql", kind=SpanKind.CLIENT
        ) as span:

            span = _hydrate_span_from_args(span, *args, **kwargs)

            try:
                result = await wrapped(*args, **kwargs)
            except Exception as exc:  # pylint: disable=W0703
                exception = exc

            if exception is not None:
                span.set_status(
                    Status(_exception_to_canonical_code(exception))
                )
            else:
                span.set_status(Status(StatusCanonicalCode.OK))

        if exception is not None:
            raise exception.with_traceback(exception.__traceback__)

        return result

    setattr(_method, _APPLIED, True)
    return _method


class AsyncPGInstrumentor(BaseInstrumentor):
    def instrument(self, **kwargs):
        self._instrument(**kwargs)

    def uninstrument(self, **kwargs):
        self._uninstrument(**kwargs)

    @staticmethod
    def _instrument(**kwargs):
        tracer_provider = kwargs.get("tracer_provider")

        for method in ["_execute", "_executemany"]:
            _original = getattr(Connection, method, None)
            if hasattr(_original, _APPLIED) is False:
                setattr(
                    Connection, method, _execute(_original, tracer_provider)
                )

    @staticmethod
    def _uninstrument(**__):
        for method in ["_execute", "_executemany"]:
            _connection_method = getattr(Connection, method, None)
            if _connection_method is not None and getattr(
                _connection_method, _APPLIED, False
            ):
                original = getattr(_connection_method, "__wrapped__", None)
                if original is not None:
                    setattr(Connection, method, original)
