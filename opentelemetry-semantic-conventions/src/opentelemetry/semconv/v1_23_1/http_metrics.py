
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

class HttpMetrics:

    """
    Size of HTTP client request bodies
    """
    @staticmethod
    def create_http_client_request_body_size(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="http.client.request.body.size",
            description="Size of HTTP client request bodies.",
            unit="By",
        )


    """
    Duration of HTTP client requests
    """
    @staticmethod
    def create_http_client_request_duration(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="http.client.request.duration",
            description="Duration of HTTP client requests.",
            unit="s",
        )


    """
    Size of HTTP client response bodies
    """
    @staticmethod
    def create_http_client_response_body_size(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="http.client.response.body.size",
            description="Size of HTTP client response bodies.",
            unit="By",
        )


    """
    Number of active HTTP server requests
    """
    @staticmethod
    def create_http_server_active_requests(meter: Meter) -> UpDownCounter:
        return meter.create_up_down_counter(
            name="http.server.active_requests",
            description="Number of active HTTP server requests.",
            unit="{request}",
        )


    """
    Size of HTTP server request bodies
    """
    @staticmethod
    def create_http_server_request_body_size(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="http.server.request.body.size",
            description="Size of HTTP server request bodies.",
            unit="By",
        )


    """
    Duration of HTTP server requests
    """
    @staticmethod
    def create_http_server_request_duration(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="http.server.request.duration",
            description="Duration of HTTP server requests.",
            unit="s",
        )


    """
    Size of HTTP server response bodies
    """
    @staticmethod
    def create_http_server_response_body_size(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="http.server.response.body.size",
            description="Size of HTTP server response bodies.",
            unit="By",
        )

