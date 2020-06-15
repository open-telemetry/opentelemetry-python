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
    from opentelemetry.ext.asyncpg import AsyncPGInstrumentor

    # You can optionally pass a custom TracerProvider to AsyncPGInstrumentor.instrument()
    AsyncPGInstrumentor().instrument()
    conn = await asyncpg.connect(user='user', password='password',
                                 database='database', host='127.0.0.1')
    values = await conn.fetch('''SELECT 42;''')

API
---
"""

import asyncpg
import wrapt
from asyncpg import exceptions

from opentelemetry import trace
from opentelemetry.ext.asyncpg.version import __version__
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.instrumentation.utils import unwrap
from opentelemetry.trace import SpanKind
from opentelemetry.trace.status import Status, StatusCanonicalCode

_APPLIED = "_opentelemetry_tracer"


def _exception_to_canonical_code(exc: Exception) -> StatusCanonicalCode:
    if isinstance(
        exc, (exceptions.InterfaceError, exceptions.SyntaxOrAccessError),
    ):
        return StatusCanonicalCode.INVALID_ARGUMENT
    if isinstance(exc, exceptions.IdleInTransactionSessionTimeoutError):
        return StatusCanonicalCode.DEADLINE_EXCEEDED
    return StatusCanonicalCode.UNKNOWN


def _hydrate_span_from_args(connection, query, parameters) -> dict:
    span_attributes = {"db.type": "sql"}

    if connection is not None:
        params = getattr(connection, "_params", None)
        if params is not None:
            database_name = getattr(params, "database", None)
            if database_name is not None:
                span_attributes["db.instance"] = database_name

            database_user = getattr(params, "user", None)
            if database_user is not None:
                span_attributes["db.user"] = database_user

    if query is not None:
        span_attributes["db.statement"] = query

    if parameters is not None and len(parameters) > 0:
        span_attributes["db.statement.parameters"] = str(parameters)

    return span_attributes


async def _do_execute(func, span_attributes, args, kwargs):
    tracer = getattr(asyncpg, _APPLIED)

    exception = None

    with tracer.start_as_current_span(
        "postgresql", kind=SpanKind.CLIENT
    ) as span:

        for k, v in span_attributes.items():
            span.set_attribute(k, v)

        try:
            result = await func(*args, **kwargs)
        except Exception as exc:  # pylint: disable=W0703
            exception = exc
            raise
        finally:
            if exception is not None:
                span.set_status(
                    Status(_exception_to_canonical_code(exception))
                )
            else:
                span.set_status(Status(StatusCanonicalCode.OK))

    return result


async def _execute(func, instance, args, kwargs):
    span_attributes = _hydrate_span_from_args(instance, args[0], args[1:])
    return await _do_execute(func, span_attributes, args, kwargs)


async def _fetch(func, instance, args, kwargs):
    span_attributes = _hydrate_span_from_args(instance, args[0], args[1:])
    return await _do_execute(func, span_attributes, args, kwargs)


class AsyncPGInstrumentor(BaseInstrumentor):
    def _instrument(self, **kwargs):
        tracer_provider = kwargs.get(
            "tracer_provider", trace.get_tracer_provider()
        )
        setattr(
            asyncpg,
            _APPLIED,
            tracer_provider.get_tracer("asyncpg", __version__),
        )
        wrapt.wrap_function_wrapper(
            "asyncpg.connection", "Connection.execute", _execute
        )
        wrapt.wrap_function_wrapper(
            "asyncpg.connection", "Connection.executemany", _execute
        )
        wrapt.wrap_function_wrapper(
            "asyncpg.connection", "Connection.fetch", _fetch
        )
        wrapt.wrap_function_wrapper(
            "asyncpg.connection", "Connection.fetchval", _fetch
        )
        wrapt.wrap_function_wrapper(
            "asyncpg.connection", "Connection.fetchrow", _fetch
        )

    def _uninstrument(self, **__):
        delattr(asyncpg, _APPLIED)
        for method in [
            "execute",
            "executemany",
            "fetch",
            "fetchval",
            "fetchrow",
        ]:
            unwrap(asyncpg.Connection, method)
