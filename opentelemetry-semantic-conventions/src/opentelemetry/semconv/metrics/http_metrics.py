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
def create_http_client_request_duration(meter: Meter) -> Histogram:
    """Duration of HTTP client requests"""
    return meter.create_histogram(
        name="http.client.request.duration",
        description="Duration of HTTP client requests.",
        unit="s",
    )


@staticmethod
def create_http_server_request_duration(meter: Meter) -> Histogram:
    """Duration of HTTP server requests"""
    return meter.create_histogram(
        name="http.server.request.duration",
        description="Duration of HTTP server requests.",
        unit="s",
    )

