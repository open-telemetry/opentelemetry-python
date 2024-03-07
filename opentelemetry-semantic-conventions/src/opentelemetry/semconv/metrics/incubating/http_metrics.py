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
def create_http_client_active_requests(meter: Meter) -> UpDownCounter:
    """Number of active HTTP requests"""
    return meter.create_up_down_counter(
        name="http.client.active_requests",
        description="Number of active HTTP requests.",
        unit="{request}",
    )


@staticmethod
def create_http_client_connection_duration(meter: Meter) -> Histogram:
    """The duration of the successfully established outbound HTTP connections"""
    return meter.create_histogram(
        name="http.client.connection.duration",
        description="The duration of the successfully established outbound HTTP connections.",
        unit="s",
    )


@staticmethod
def create_http_client_open_connections(meter: Meter) -> UpDownCounter:
    """Number of outbound HTTP connections that are currently active or idle on the client"""
    return meter.create_up_down_counter(
        name="http.client.open_connections",
        description="Number of outbound HTTP connections that are currently active or idle on the client.",
        unit="{connection}",
    )


@staticmethod
def create_http_client_request_body_size(meter: Meter) -> Histogram:
    """Size of HTTP client request bodies"""
    return meter.create_histogram(
        name="http.client.request.body.size",
        description="Size of HTTP client request bodies.",
        unit="By",
    )


@staticmethod
def create_http_client_request_duration(meter: Meter) -> Histogram:
    """Duration of HTTP client requests"""
    return meter.create_histogram(
        name="http.client.request.duration",
        description="Duration of HTTP client requests.",
        unit="s",
    )


@staticmethod
def create_http_client_request_time_in_queue(meter: Meter) -> Histogram:
    """The amount of time requests spent on a queue waiting for an available connection"""
    return meter.create_histogram(
        name="http.client.request.time_in_queue",
        description="The amount of time requests spent on a queue waiting for an available connection.",
        unit="s",
    )


@staticmethod
def create_http_client_response_body_size(meter: Meter) -> Histogram:
    """Size of HTTP client response bodies"""
    return meter.create_histogram(
        name="http.client.response.body.size",
        description="Size of HTTP client response bodies.",
        unit="By",
    )


@staticmethod
def create_http_server_active_requests(meter: Meter) -> UpDownCounter:
    """Number of active HTTP server requests"""
    return meter.create_up_down_counter(
        name="http.server.active_requests",
        description="Number of active HTTP server requests.",
        unit="{request}",
    )


@staticmethod
def create_http_server_request_body_size(meter: Meter) -> Histogram:
    """Size of HTTP server request bodies"""
    return meter.create_histogram(
        name="http.server.request.body.size",
        description="Size of HTTP server request bodies.",
        unit="By",
    )


@staticmethod
def create_http_server_request_duration(meter: Meter) -> Histogram:
    """Duration of HTTP server requests"""
    return meter.create_histogram(
        name="http.server.request.duration",
        description="Duration of HTTP server requests.",
        unit="s",
    )


@staticmethod
def create_http_server_response_body_size(meter: Meter) -> Histogram:
    """Size of HTTP server response bodies"""
    return meter.create_histogram(
        name="http.server.response.body.size",
        description="Size of HTTP server response bodies.",
        unit="By",
    )

