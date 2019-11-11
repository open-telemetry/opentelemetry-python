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

import typing

import mysql.connector
import wrapt

from opentelemetry.ext.dbapi import DatabaseApiTracer
from opentelemetry.trace import Tracer


def trace_integration(tracer: Tracer):
    """Integrate with MySQL Connector/Python library.
       https://dev.mysql.com/doc/connector-python/en/
    """

    # pylint: disable=unused-argument
    def wrap(
        wrapped: typing.Callable[..., any],
        instance: typing.Any,
        args: typing.Tuple[any, any],
        kwargs: typing.Dict[any, any],
    ):
        """Patch MySQL Connector connect method to add tracing.
        """
        mysql_tracer = DatabaseApiTracer(tracer, "mysql")
        return mysql_tracer.wrap_connect(wrapped, args, kwargs)

    wrapt.wrap_function_wrapper(mysql.connector, "connect", wrap)
