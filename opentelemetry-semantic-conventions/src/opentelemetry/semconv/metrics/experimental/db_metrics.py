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

from opentelemetry.metrics import (
    Counter,
    Histogram,
    Meter,
    UpDownCounter,
    ObservableGauge,
)

from typing import Callable, Sequence

@staticmethod
def create_db_client_connections_create_time(meter: Meter) -> Histogram:
    """The time it took to create a new connection"""
    return meter.create_histogram(
        name="db.client.connections.create_time",
        description="The time it took to create a new connection",
        unit="ms",
    )


@staticmethod
def create_db_client_connections_idle_max(meter: Meter) -> UpDownCounter:
    """The maximum number of idle open connections allowed"""
    return meter.create_up_down_counter(
        name="db.client.connections.idle.max",
        description="The maximum number of idle open connections allowed",
        unit="{connection}",
    )


@staticmethod
def create_db_client_connections_idle_min(meter: Meter) -> UpDownCounter:
    """The minimum number of idle open connections allowed"""
    return meter.create_up_down_counter(
        name="db.client.connections.idle.min",
        description="The minimum number of idle open connections allowed",
        unit="{connection}",
    )


@staticmethod
def create_db_client_connections_max(meter: Meter) -> UpDownCounter:
    """The maximum number of open connections allowed"""
    return meter.create_up_down_counter(
        name="db.client.connections.max",
        description="The maximum number of open connections allowed",
        unit="{connection}",
    )


@staticmethod
def create_db_client_connections_pending_requests(meter: Meter) -> UpDownCounter:
    """The number of pending requests for an open connection, cumulative for the entire pool"""
    return meter.create_up_down_counter(
        name="db.client.connections.pending_requests",
        description="The number of pending requests for an open connection, cumulative for the entire pool",
        unit="{request}",
    )


@staticmethod
def create_db_client_connections_timeouts(meter: Meter) -> Counter:
    """The number of connection timeouts that have occurred trying to obtain a connection from the pool"""
    return meter.create_counter(
        name="db.client.connections.timeouts",
        description="The number of connection timeouts that have occurred trying to obtain a connection from the pool",
        unit="{timeout}",
    )


@staticmethod
def create_db_client_connections_usage(meter: Meter) -> UpDownCounter:
    """The number of connections that are currently in state described by the `state` attribute"""
    return meter.create_up_down_counter(
        name="db.client.connections.usage",
        description="The number of connections that are currently in state described by the `state` attribute",
        unit="{connection}",
    )


@staticmethod
def create_db_client_connections_use_time(meter: Meter) -> Histogram:
    """The time between borrowing a connection and returning it to the pool"""
    return meter.create_histogram(
        name="db.client.connections.use_time",
        description="The time between borrowing a connection and returning it to the pool",
        unit="ms",
    )


@staticmethod
def create_db_client_connections_wait_time(meter: Meter) -> Histogram:
    """The time it took to obtain an open connection from the pool"""
    return meter.create_histogram(
        name="db.client.connections.wait_time",
        description="The time it took to obtain an open connection from the pool",
        unit="ms",
    )

