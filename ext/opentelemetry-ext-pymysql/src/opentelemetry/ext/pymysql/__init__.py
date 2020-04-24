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
The integration with PyMySQL supports the `PyMySQL`_ library and can be enabled
by using ``PyMySQLInstrumentor``.

.. _PyMySQL: https://pypi.org/project/PyMySQL/

Usage
-----

.. code:: python

    import pymysql
    from opentelemetry import trace
    from opentelemetry.ext.pymysql import PyMySQLInstrumentor
    from opentelemetry.sdk.trace import TracerProvider

    trace.set_tracer_provider(TracerProvider())

    PyMySQLInstrumentor().instrument()

    cnx = pymysql.connect(database="MySQL_Database")
    cursor = cnx.cursor()
    cursor.execute("INSERT INTO test (testField) VALUES (123)"
    cnx.commit()
    cursor.close()
    cnx.close()

API
---
"""

import typing

import pymysql

from opentelemetry.auto_instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.ext import dbapi
from opentelemetry.ext.pymysql.version import __version__
from opentelemetry.trace import TracerProvider, get_tracer


class PyMySQLInstrumentor(BaseInstrumentor):
    _CONNECTION_ATTRIBUTES = {
        "database": "db",
        "port": "port",
        "host": "host",
        "user": "user",
    }

    _DATABASE_COMPONENT = "mysql"
    _DATABASE_TYPE = "sql"

    def _instrument(self, **kwargs):
        """Integrate with the PyMySQL library.
        https://github.com/PyMySQL/PyMySQL/
        """
        tracer_provider = kwargs.get("tracer_provider")

        tracer = get_tracer(__name__, __version__, tracer_provider)

        dbapi.wrap_connect(
            tracer,
            pymysql,
            "connect",
            self._DATABASE_COMPONENT,
            self._DATABASE_TYPE,
            self._CONNECTION_ATTRIBUTES,
        )

    def _uninstrument(self, **kwargs):
        """"Disable PyMySQL instrumentation"""
        dbapi.unwrap_connect(pymysql, "connect")

    # pylint:disable=no-self-use
    def instrument_connection(self, connection):
        """Enable instrumentation in a PyMySQL connection.

            Args:
                connection: The connection to instrument.
        """
        tracer = get_tracer(__name__, __version__)

        return dbapi.instrument_connection(
            tracer,
            connection,
            self._DATABASE_COMPONENT,
            self._DATABASE_TYPE,
            self._CONNECTION_ATTRIBUTES,
        )

    def uninstrument_connection(self, connection):
        """Disable instrumentation in a PyMySQL connection.

            Args:
                connection: The connection to uninstrument.
        """
        return dbapi.uninstrument_connection(connection)
