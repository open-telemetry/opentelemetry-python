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
The opentelemetry-ext-mysql package allows tracing MySQL queries made by the
MySQL Connector/Python library.
"""

import mysql.connector
from opentelemetry.ext.dbapi import trace_integration as db_integration
from opentelemetry.trace import Tracer


def trace_integration(tracer: Tracer):
    """Integrate with MySQL Connector/Python library.
       https://dev.mysql.com/doc/connector-python/en/
    """
    connection_attributes = {
        "database": "database",
        "port": "server_port",
        "host": "server_host",
        "user": "user",
    }
    db_integration(
        tracer,
        mysql.connector,
        "connect",
        "mysql",
        "sql",
        connection_attributes,
    )
