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


def trace_integration(
    tracer: Tracer,
    connect_module: typing.Callable[..., any],
    connect_method_name: str,
    database_component: str,
    database_type: str = "",
    connection_attributes: typing.Dict = None,
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
        db_integration = DatabaseApiIntegration(
            tracer,
            database_component,
            database_type=database_type,
            connection_attributes=connection_attributes,
        )
        return db_integration.wrapped_connection(wrapped, args, kwargs)

    try:
        wrapt.wrap_function_wrapper(
            connect_module, connect_method_name, wrap_connect
        )
    except Exception as ex:  # pylint: disable=broad-except
        logging.warning("Failed to integrate with DB API. %s", str(ex))


class DatabaseApiIntegration:
    # pylint: disable=unused-argument
    def __init__(
        self,
        tracer: Tracer,
        database_component: str,
        database_type: str = "sql",
        connection_attributes=None,
    ):
        if tracer is None:
            raise ValueError("The tracer is not provided.")
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

    def wrapped_connection(
        self,
        connect_method: typing.Callable[..., any],
        args: typing.Tuple[any, any],
        kwargs: typing.Dict[any, any],
    ):
        """Add object proxy to connection object.
        """
        connection = connect_method(*args, **kwargs)

        for key, value in self.connection_attributes.items():
            attribute = getattr(connection, value, None)
            if attribute:
                self.connection_props[key] = attribute

        traced_connection = TracedConnection(connection, self)
        return traced_connection


class TracedConnection(wrapt.ObjectProxy):

    # pylint: disable=unused-argument
    def __init__(
        self,
        connection,
        db_api_integration: DatabaseApiIntegration,
        *args,
        **kwargs,
    ):
        wrapt.ObjectProxy.__init__(self, connection)
        self._db_api_integration = db_api_integration

    def cursor(self, *args, **kwargs):
        return TracedCursor(
            self.__wrapped__.cursor(*args, **kwargs), self._db_api_integration
        )


class TracedCursor(wrapt.ObjectProxy):
    
    # pylint: disable=unused-argument
    def __init__(
        self,
        cursor,
        db_api_integration: DatabaseApiIntegration,
        *args,
        **kwargs,
    ):
        wrapt.ObjectProxy.__init__(self, cursor)
        self._db_api_integration = db_api_integration

    def execute(self, *args, **kwargs):
        return self._traced_execution(
            self.__wrapped__.execute, *args, **kwargs
        )

    def executemany(self, *args, **kwargs):
        return self._traced_execution(
            self.__wrapped__.executemany, *args, **kwargs
        )

    def callproc(self, *args, **kwargs):
        return self._traced_execution(
            self.__wrapped__.callproc, *args, **kwargs
        )

    def _traced_execution(
        self,
        query_method: typing.Callable[..., any],
        *args: typing.Tuple[any, any],
        **kwargs: typing.Dict[any, any],
    ):

        statement = args[0] if args else ""
        name = self._db_api_integration.database_component
        database = self._db_api_integration.connection_props.get(
            "database", ""
        )
        if database:
            name += "." + database

        with self._db_api_integration.tracer.start_as_current_span(
            name, kind=SpanKind.CLIENT
        ) as span:
            span.set_attribute(
                "component", self._db_api_integration.database_component
            )
            span.set_attribute(
                "db.type", self._db_api_integration.database_type
            )
            span.set_attribute("db.instance", database)
            span.set_attribute("db.statement", statement)

            user = self._db_api_integration.connection_props.get("user")
            if user is not None:
                span.set_attribute("db.user", user)
            host = self._db_api_integration.connection_props.get("host")
            if host is not None:
                span.set_attribute("peer.hostname", host)
            port = self._db_api_integration.connection_props.get("port")
            if port is not None:
                span.set_attribute("peer.port", port)

            if len(args) > 1:
                span.set_attribute("db.statement.parameters", str(args[1]))

            try:
                result = query_method(*args, **kwargs)
                span.set_status(Status(StatusCanonicalCode.OK))
                return result
            except Exception as ex:  # pylint: disable=broad-except
                span.set_status(Status(StatusCanonicalCode.UNKNOWN, str(ex)))
                raise ex
