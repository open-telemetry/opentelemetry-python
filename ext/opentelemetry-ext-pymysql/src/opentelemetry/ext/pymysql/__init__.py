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
The integration with PyMySQL supports the `PyMySQL`_ library and is specified
to ``trace_integration`` using ``'PyMySQL'``.

.. _PyMySQL: https://pypi.org/project/PyMySQL/

Usage
-----

.. code:: python

    import pymysql
    from opentelemetry import trace
    from opentelemetry.ext.pymysql import trace_integration
    from opentelemetry.sdk.trace import TracerProvider

    trace.set_tracer_provider(TracerProvider())
    trace_integration()
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

from opentelemetry.ext.dbapi import wrap_connect
from opentelemetry.ext.pymysql.version import __version__
from opentelemetry.trace import TracerProvider, get_tracer


def trace_integration(tracer_provider: typing.Optional[TracerProvider] = None):
    """Integrate with the PyMySQL library.
       https://github.com/PyMySQL/PyMySQL/
    """

    tracer = get_tracer(__name__, __version__, tracer_provider)

    connection_attributes = {
        "database": "db",
        "port": "port",
        "host": "host",
        "user": "user",
    }
    wrap_connect(
        tracer, pymysql, "connect", "mysql", "sql", connection_attributes
    )
