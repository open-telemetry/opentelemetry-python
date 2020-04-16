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
The integration with PostgreSQL supports the `Psycopg`_ library and is specified
to ``trace_integration`` using ``'PostgreSQL'``.

.. _Psycopg: http://initd.org/psycopg/

Usage
-----

.. code-block:: python

    import psycopg2
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.trace.ext.psycopg2 import trace_integration

    trace.set_tracer_provider(TracerProvider())

    trace_integration()
    cnx = psycopg2.connect(database='Database')
    cursor = cnx.cursor()
    cursor.execute("INSERT INTO test (testField) VALUES (123)")
    cursor.close()
    cnx.close()

API
---
"""

import logging
import typing

import psycopg2
import wrapt
from psycopg2.sql import Composable

from opentelemetry.ext.dbapi import DatabaseApiIntegration, TracedCursor
from opentelemetry.ext.psycopg2.version import __version__
from opentelemetry.trace import Tracer, get_tracer_provider

logger = logging.getLogger(__name__)

DATABASE_COMPONENT = "postgresql"
DATABASE_TYPE = "sql"


def trace_integration(tracer_provider=None):
    """Integrate with PostgreSQL Psycopg library.
       Psycopg: http://initd.org/psycopg/
    """

    if tracer_provider is None:
        tracer_provider = get_tracer_provider()

    tracer = tracer_provider.get_tracer(__name__, __version__)

    connection_attributes = {
        "database": "info.dbname",
        "port": "info.port",
        "host": "info.host",
        "user": "info.user",
    }
    db_integration = DatabaseApiIntegration(
        tracer,
        DATABASE_COMPONENT,
        database_type=DATABASE_TYPE,
        connection_attributes=connection_attributes,
    )

    # pylint: disable=unused-argument
    def wrap_connect(
        connect_func: typing.Callable[..., any],
        instance: typing.Any,
        args: typing.Tuple[any, any],
        kwargs: typing.Dict[any, any],
    ):
        connection = connect_func(*args, **kwargs)
        db_integration.get_connection_attributes(connection)
        connection.cursor_factory = PsycopgTraceCursor
        return connection

    try:
        wrapt.wrap_function_wrapper(psycopg2, "connect", wrap_connect)
    except Exception as ex:  # pylint: disable=broad-except
        logger.warning("Failed to integrate with pyscopg2. %s", str(ex))

    class PsycopgTraceCursor(psycopg2.extensions.cursor):
        def __init__(self, *args, **kwargs):
            self._traced_cursor = TracedCursor(db_integration)
            super(PsycopgTraceCursor, self).__init__(*args, **kwargs)

        # pylint: disable=redefined-builtin
        def execute(self, query, vars=None):
            if isinstance(query, Composable):
                query = query.as_string(self)
            return self._traced_cursor.traced_execution(
                super(PsycopgTraceCursor, self).execute, query, vars
            )

        # pylint: disable=redefined-builtin
        def executemany(self, query, vars):
            if isinstance(query, Composable):
                query = query.as_string(self)
            return self._traced_cursor.traced_execution(
                super(PsycopgTraceCursor, self).executemany, query, vars
            )

        # pylint: disable=redefined-builtin
        def callproc(self, procname, vars=None):
            return self._traced_cursor.traced_execution(
                super(PsycopgTraceCursor, self).callproc, procname, vars
            )
