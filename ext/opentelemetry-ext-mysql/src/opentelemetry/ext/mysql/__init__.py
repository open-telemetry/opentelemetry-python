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
The integration with MySQL supports the `mysql-connector`_ library and is specified
to ``trace_integration`` using ``'MySQL'``.

.. _mysql-connector: https://pypi.org/project/mysql-connector/

Usage
-----

.. code:: python

    import mysql.connector
    from opentelemetry import trace
    from opentelemetry.trace import TracerProvider
    from opentelemetry.ext.mysql import trace_integration

    trace.set_tracer_provider(TracerProvider())

    trace_integration()
    cnx = mysql.connector.connect(database='MySQL_Database')
    cursor = cnx.cursor()
    cursor.execute("INSERT INTO test (testField) VALUES (123)"
    cursor.close()
    cnx.close()

API
---
"""

import typing

import mysql.connector

from opentelemetry.ext.dbapi import wrap_connect
from opentelemetry.ext.mysql.version import __version__
from opentelemetry.trace import TracerProvider, get_tracer


def trace_integration(tracer_provider: typing.Optional[TracerProvider] = None):
    """Integrate with MySQL Connector/Python library.
       https://dev.mysql.com/doc/connector-python/en/
    """

    tracer = get_tracer(__name__, __version__, tracer_provider)

    connection_attributes = {
        "database": "database",
        "port": "server_port",
        "host": "server_host",
        "user": "user",
    }
    wrap_connect(
        tracer,
        mysql.connector,
        "connect",
        "mysql",
        "sql",
        connection_attributes,
    )
