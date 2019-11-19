# Copyright 2019, OpenTelemetry Authors
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
The opentelemetry-ext-postgresql package allows tracing PostgreSQL queries made by the
Psycopg2 library.
"""

import typing

import psycopg2
from psycopg2.extensions import cursor as pgcursor
import wrapt

from opentelemetry.context import Context
from opentelemetry.trace import SpanKind, Tracer
from opentelemetry.trace.status import Status, StatusCanonicalCode

QUERY_WRAP_METHODS = ["execute", "executemany", "callproc"]
DATABASE_COMPONENT = "postgresql"
DATABASE_TYPE = "sql"


def trace_integration(tracer):
    """Integrate with PostgreSQL Psycopg library.
       Psycopg: http://initd.org/psycopg/
    """

    if tracer is None:
        raise ValueError("The tracer is not provided.")

    # pylint: disable=unused-argument
    def wrap(wrapped, instance, args, kwargs):
        """Patch Psycopg connect method.
        """
        connection = wrapped(*args, **kwargs)
        connection.cursor_factory = TraceCursor
        return connection

    wrapt.wrap_function_wrapper(psycopg2, "connect", wrap)

    class TraceCursor(pgcursor):
        def __init__(self, *args, **kwargs):
            for func in QUERY_WRAP_METHODS:
                wrapt.wrap_function_wrapper(self, func, self.add_span)
            super(TraceCursor, self).__init__(*args, **kwargs)

        def add_span(
            self,
            wrapped: typing.Callable[..., any],
            instance: typing.Any,
            args: typing.Tuple[any, any],
            kwargs: typing.Dict[any, any],
        ):

            name = DATABASE_COMPONENT
            database = self.connection.info.dbname
            if database:
                name += "." + database

            query = args[0] if args else ""
            # Query with parameters
            if len(args) > 1:
                query += " params=" + str(args[1])

            with tracer.start_current_span(name, kind=SpanKind.CLIENT) as span:
                span.set_attribute("component", DATABASE_COMPONENT)
                span.set_attribute("db.type", DATABASE_TYPE)
                span.set_attribute("db.instance", database)
                span.set_attribute("db.statement", query)
                span.set_attribute("db.user", self.connection.info.user)
                span.set_attribute("peer.hostname", self.connection.info.host)
                port = self.connection.info.port
                if port is not None:
                    span.set_attribute("peer.port", port)
                try:
                    result = wrapped(*args, **kwargs)
                    span.set_status(Status(StatusCanonicalCode.OK))
                    return result
                except Exception as ex:  # pylint: disable=broad-except
                    span.set_status(
                        Status(StatusCanonicalCode.UNKNOWN, str(ex))
                    )
