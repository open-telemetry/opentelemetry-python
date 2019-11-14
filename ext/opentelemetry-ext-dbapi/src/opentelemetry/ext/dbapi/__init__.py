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
The opentelemetry-ext-dbapi package allows tracing queries made by the
ibraries following Ptyhon Database API specification:
https://www.python.org/dev/peps/pep-0249/
"""

import typing

import wrapt

from opentelemetry.trace import SpanKind, Tracer
from opentelemetry.trace.status import Status, StatusCanonicalCode

QUERY_WRAP_METHODS = ["execute", "executemany", "callproc"]


class DatabaseApiTracer:
    def __init__(
        self, tracer: Tracer, database_component: str, database_type="sql"
    ):
        if tracer is None:
            raise ValueError("The tracer is not provided.")
        self._tracer = tracer
        self._database_component = database_component
        self._database_type = database_type
        self._connection_props = {}

    def wrap_connect(
        self,
        wrapped: typing.Callable[..., any],
        args: typing.Tuple[any, any],
        kwargs: typing.Dict[any, any],
    ):
        """Patch connect method to add tracing.
        """
        connection = wrapped(*args, **kwargs)
        self._connection_props = {
            "database": connection.database,
            "port": connection.server_port,
            "host": connection.server_host,
            "user": connection.user,
        }

        wrapt.wrap_function_wrapper(connection, "cursor", self.wrap_cursor)
        return connection

    # pylint: disable=unused-argument
    def wrap_cursor(
        self,
        wrapped: typing.Callable[..., any],
        instance: typing.Any,
        args: typing.Tuple[any, any],
        kwargs: typing.Dict[any, any],
    ):
        """Patch cursor instance in a specific connection.
        """
        cursor = wrapped(*args, **kwargs)
        for func in QUERY_WRAP_METHODS:
            wrapt.wrap_function_wrapper(cursor, func, self.add_span)
        return cursor

    # pylint: disable=unused-argument
    def add_span(
        self,
        wrapped: typing.Callable[..., any],
        instance: typing.Any,
        args: typing.Tuple[any, any],
        kwargs: typing.Dict[any, any],
    ):
        """Patch execute, executeMany and callproc methods in cursor and create span.
        """
        name = self._database_component
        database = self._connection_props.get("database", "")
        if database:
            name += "." + database
        query = args[0] if args else ""
        # Query with parameters
        if len(args) > 1:
            query += " params=" + str(args[1])

        with self._tracer.start_as_current_span(
            name, kind=SpanKind.CLIENT
        ) as span:
            span.set_attribute("component", self._database_component)
            span.set_attribute("db.type", self._database_type)
            span.set_attribute("db.instance", database)
            span.set_attribute("db.statement", query)
            span.set_attribute(
                "db.user", self._connection_props.get("user", "")
            )
            span.set_attribute(
                "peer.hostname", self._connection_props.get("host", "")
            )
            port = self._connection_props.get("port")
            if port is not None:
                span.set_attribute("peer.port", port)

            try:
                result = wrapped(*args, **kwargs)
                span.set_status(Status(StatusCanonicalCode.OK))
                return result
            except Exception as ex:  # pylint: disable=broad-except
                span.set_status(Status(StatusCanonicalCode.UNKNOWN, str(ex)))
