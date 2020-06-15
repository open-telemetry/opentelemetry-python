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
The trace integration with aiopg based on dbapi integration,
where replaced sync wrap methods to async

Usage
-----

.. code-block:: python

    from opentelemetry import trace
    from opentelemetry.ext.aiopg import trace_integration
    from opentelemetry.trace import TracerProvider

    trace.set_tracer_provider(TracerProvider())

    trace_integration(aiopg.connection, "_connect", "postgresql", "sql")

API
---
"""
import logging
import typing

import wrapt

from opentelemetry.ext.aiopg.aiopg_integration import (
    AiopgIntegration,
    get_traced_connection_proxy,
)
from opentelemetry.ext.aiopg.version import __version__
from opentelemetry.instrumentation.utils import unwrap
from opentelemetry.trace import Tracer, TracerProvider, get_tracer

logger = logging.getLogger(__name__)


def trace_integration(
    connect_module: typing.Callable[..., typing.Any],
    connect_method_name: str,
    database_component: str,
    database_type: str = "",
    connection_attributes: typing.Dict = None,
    tracer_provider: typing.Optional[TracerProvider] = None,
):
    """Integrate with aiopg library.
        based on dbapi integration, where replaced sync wrap methods to async

        Args:
            connect_module: Module name where connect method is available.
            connect_method_name: The connect method name.
            database_component: Database driver name or
                database name "postgreSQL".
            database_type: The Database type. For any SQL database, "sql".
            connection_attributes: Attribute names for database, port, host and
                user in Connection object.
            tracer_provider: The :class:`opentelemetry.trace.TracerProvider` to
                use. If ommited the current configured one is used.
    """
    tracer = get_tracer(__name__, __version__, tracer_provider)
    wrap_connect(
        tracer,
        connect_module,
        connect_method_name,
        database_component,
        database_type,
        connection_attributes,
    )


def wrap_connect(
    tracer: Tracer,
    connect_module: typing.Callable[..., typing.Any],
    connect_method_name: str,
    database_component: str,
    database_type: str = "",
    connection_attributes: typing.Dict = None,
):
    """Integrate with aiopg library.
        https://github.com/aio-libs/aiopg

        Args:
            tracer: The :class:`opentelemetry.trace.Tracer` to use.
            connect_module: Module name where connect method is available.
            connect_method_name: The connect method name.
            database_component: Database driver name
                or database name "postgreSQL".
            database_type: The Database type. For any SQL database, "sql".
            connection_attributes: Attribute names for database, port, host and
                user in Connection object.
    """

    # pylint: disable=unused-argument
    async def wrap_connect_(
        wrapped: typing.Callable[..., typing.Any],
        instance: typing.Any,
        args: typing.Tuple[typing.Any, typing.Any],
        kwargs: typing.Dict[typing.Any, typing.Any],
    ):
        db_integration = AiopgIntegration(
            tracer,
            database_component,
            database_type=database_type,
            connection_attributes=connection_attributes,
        )
        return await db_integration.wrapped_connection(wrapped, args, kwargs)

    try:
        wrapt.wrap_function_wrapper(
            connect_module, connect_method_name, wrap_connect_
        )
    except Exception as ex:  # pylint: disable=broad-except
        logger.warning("Failed to integrate with aiopg. %s", str(ex))


def unwrap_connect(
    connect_module: typing.Callable[..., typing.Any], connect_method_name: str,
):
    """"Disable integration with aiopg library.
        https://github.com/aio-libs/aiopg

        Args:
            connect_module: Module name where the connect method is available.
            connect_method_name: The connect method name.
    """
    unwrap(connect_module, connect_method_name)


def instrument_connection(
    tracer,
    connection,
    database_component: str,
    database_type: str = "",
    connection_attributes: typing.Dict = None,
):
    """Enable instrumentation in a database connection.

    Args:
        tracer: The :class:`opentelemetry.trace.Tracer` to use.
        connection: The connection to instrument.
        database_component: Database driver name or database name "postgreSQL".
        database_type: The Database type. For any SQL database, "sql".
        connection_attributes: Attribute names for database, port, host and
            user in a connection object.

    Returns:
        An instrumented connection.
    """
    db_integration = AiopgIntegration(
        tracer,
        database_component,
        database_type,
        connection_attributes=connection_attributes,
    )
    db_integration.get_connection_attributes(connection)
    return get_traced_connection_proxy(connection, db_integration)


def uninstrument_connection(connection):
    """Disable instrumentation in a database connection.

    Args:
        connection: The connection to uninstrument.

    Returns:
        An uninstrumented connection.
    """
    if isinstance(connection, wrapt.ObjectProxy):
        return connection.__wrapped__

    logger.warning("Connection is not instrumented")
    return connection


def wrap_create_pool(
    tracer: Tracer,
    create_pool_module: typing.Callable[..., typing.Any],
    create_pool_method_name: str,
    database_component: str,
    database_type: str = "",
    connection_attributes: typing.Dict = None,
):
    # pylint: disable=unused-argument
    async def wrap_create_pool_(
        wrapped: typing.Callable[..., typing.Any],
        instance: typing.Any,
        args: typing.Tuple[typing.Any, typing.Any],
        kwargs: typing.Dict[typing.Any, typing.Any],
    ):
        db_integration = AiopgIntegration(
            tracer,
            database_component,
            database_type=database_type,
            connection_attributes=connection_attributes,
        )
        return await db_integration.wrapped_pool(wrapped, args, kwargs)

    try:
        wrapt.wrap_function_wrapper(
            create_pool_module, create_pool_method_name, wrap_create_pool_
        )
    except Exception as ex:  # pylint: disable=broad-except
        logger.warning("Failed to integrate with DB API. %s", str(ex))


def unwrap_create_pool(
    create_pool_module: typing.Callable[..., typing.Any],
    create_pool_method_name: str,
):
    """"Disable integration with aiopg library.
        https://github.com/aio-libs/aiopg

        Args:
            create_pool_module: Module name where the create_pool method
                is available.
            create_pool_method_name: The connect method name.
    """
    unwrap(create_pool_module, create_pool_method_name)
