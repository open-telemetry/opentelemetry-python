# Copyright 2020, OpenTelemetry Authors
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
The opentelemetry-ext-psycopg2 package allows tracing PostgreSQL queries made by the
Psycopg2 library.
"""

import logging
import typing

import psycopg2
from psycopg2.extensions import cursor as pgcursor
import wrapt

from opentelemetry.ext.dbapi import DatabaseApiIntegration, TracedConnection, TracedCursor
from opentelemetry.trace import Tracer

logger = logging.getLogger(__name__)

DATABASE_COMPONENT = "postgresql"
DATABASE_TYPE = "sql"


def trace_integration(tracer):
    """Integrate with PostgreSQL Psycopg library.
       Psycopg: http://initd.org/psycopg/
    """

    connection_attributes = {
        "database": "info.dbname",
        "port": "info.port",
        "host": "info.host",
        "user": "info.user",
    }

     # pylint: disable=unused-argument
    def wrap_connect(
        wrapped: typing.Callable[..., any],
        instance: typing.Any,
        args: typing.Tuple[any, any],
        kwargs: typing.Dict[any, any],
    ):
        db_integration = DatabaseApiIntegration(
            tracer,
            DATABASE_COMPONENT,
            database_type=DATABASE_TYPE,
            connection_attributes=connection_attributes
        )
        return db_integration.wrapped_connection(wrapped, args, kwargs)

    try:
        wrapt.wrap_function_wrapper(
            psycopg2, "connect", wrap_connect
        )
    except Exception as ex:  # pylint: disable=broad-except
        logger.warning("Failed to integrate with pyscopg2. %s", str(ex))