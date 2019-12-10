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

import logging
import typing

import wrapt

from opentelemetry.trace import SpanKind, Tracer
from opentelemetry.trace.status import Status, StatusCanonicalCode

QUERY_WRAP_METHODS = ["execute", "executemany", "callproc"]


def trace_integration(
    tracer: Tracer,
    connect_module: typing.Callable[..., any],
    connect_method_name: str,
    database_component: str,
):
    """Integrate with DB API library.
       https://www.python.org/dev/peps/pep-0249/
    """
    # pylint: disable=unused-argument
    def wrap_connect(
        wrapped: typing.Callable[..., any],
        instance: typing.Any,
        args: typing.Tuple[any, any],
        kwargs: typing.Dict[any, any],
    ):
        db_integration = DatabaseApiIntegration(tracer, database_component)
        return db_integration.wrapped_connection(wrapped, args, kwargs)

    try:
        wrapt.wrap_function_wrapper(
            connect_module, connect_method_name, wrap_connect
        )
    except Exception as ex:  # pylint: disable=broad-except
        logging.warning("Failed to integrate with DB API. %s", str(ex))


class DatabaseApiIntegration:
    def __init__(
        self, tracer: Tracer, database_component: str, database_type="sql"
    ):
        if tracer is None:
            raise ValueError("The tracer is not provided.")
        self._tracer = tracer
        self._database_component = database_component
        self._database_type = database_type
        self._connection_props = {}

    def wrapped_connection(
        self,
        wrapped: typing.Callable[..., any],
        args: typing.Tuple[any, any],
        kwargs: typing.Dict[any, any],
    ):
        """Patch connection cursor to add tracing.
        """
        connection = wrapped(*args, **kwargs)
        self._connection_props = {
            "database": connection.database,
            "port": connection.server_port,
            "host": connection.server_host,
            "user": connection.user,
        }

        wrapt.wrap_function_wrapper(connection, "cursor", self.wrapped_cursor)
        return connection

    # pylint: disable=unused-argument
    def wrapped_cursor(
        self,
        wrapped: typing.Callable[..., any],
        instance: typing.Any,
        args: typing.Tuple[any, any],
        kwargs: typing.Dict[any, any],
    ):
        """Patch cursor execute, executemany and callproc methods.
        """
        cursor = wrapped(*args, **kwargs)
        for func in QUERY_WRAP_METHODS:
            if getattr(cursor, func, None):
                wrapt.wrap_function_wrapper(
                    cursor, func, self.wrapped_query_methods
                )
        return cursor

    # pylint: disable=unused-argument
    def wrapped_query_methods(
        self,
        wrapped: typing.Callable[..., any],
        instance: typing.Any,
        args: typing.Tuple[any, any],
        kwargs: typing.Dict[any, any],
    ):
        statement = args[0] if args else ""
        parameters = str(args[1]) if len(args) > 1 else None
        span = self.create_span(self._connection_props, statement, parameters)
        try:
            result = wrapped(*args, **kwargs)
            span.set_status(Status(StatusCanonicalCode.OK))
            return result
        except Exception as ex:  # pylint: disable=broad-except
            span.set_status(Status(StatusCanonicalCode.UNKNOWN, str(ex)))
            raise ex

    def create_span(
        self,
        connection_properties: typing.Dict,
        statement: str,
        parameters: str,
    ):
        name = self._database_component
        database = connection_properties.get("database", "")
        if database:
            name += "." + database

        with self._tracer.start_as_current_span(
            name, kind=SpanKind.CLIENT
        ) as span:
            span.set_attribute("component", self._database_component)
            span.set_attribute("db.type", self._database_type)
            span.set_attribute("db.instance", database)
            span.set_attribute("db.statement", statement)
            span.set_attribute(
                "db.user", connection_properties.get("user", "")
            )
            span.set_attribute(
                "peer.hostname", connection_properties.get("host", "")
            )
            port = connection_properties.get("port")
            if port is not None:
                span.set_attribute("peer.port", port)

            if parameters:
                span.set_attribute("db.statement.parameters", parameters)
            return span
