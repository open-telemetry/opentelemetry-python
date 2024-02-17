
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

class RpcMetrics:

    """
    Measures the duration of outbound RPC
    """
    @staticmethod
    def create_rpc_client_duration(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="rpc.client.duration",
            description="Measures the duration of outbound RPC.",
            unit="ms",
        )


    """
    Measures the size of RPC request messages (uncompressed)
    """
    @staticmethod
    def create_rpc_client_request_size(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="rpc.client.request.size",
            description="Measures the size of RPC request messages (uncompressed).",
            unit="By",
        )


    """
    Measures the number of messages received per RPC
    """
    @staticmethod
    def create_rpc_client_requests_per_rpc(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="rpc.client.requests_per_rpc",
            description="Measures the number of messages received per RPC.",
            unit="{count}",
        )


    """
    Measures the size of RPC response messages (uncompressed)
    """
    @staticmethod
    def create_rpc_client_response_size(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="rpc.client.response.size",
            description="Measures the size of RPC response messages (uncompressed).",
            unit="By",
        )


    """
    Measures the number of messages sent per RPC
    """
    @staticmethod
    def create_rpc_client_responses_per_rpc(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="rpc.client.responses_per_rpc",
            description="Measures the number of messages sent per RPC.",
            unit="{count}",
        )


    """
    Measures the duration of inbound RPC
    """
    @staticmethod
    def create_rpc_server_duration(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="rpc.server.duration",
            description="Measures the duration of inbound RPC.",
            unit="ms",
        )


    """
    Measures the size of RPC request messages (uncompressed)
    """
    @staticmethod
    def create_rpc_server_request_size(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="rpc.server.request.size",
            description="Measures the size of RPC request messages (uncompressed).",
            unit="By",
        )


    """
    Measures the number of messages received per RPC
    """
    @staticmethod
    def create_rpc_server_requests_per_rpc(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="rpc.server.requests_per_rpc",
            description="Measures the number of messages received per RPC.",
            unit="{count}",
        )


    """
    Measures the size of RPC response messages (uncompressed)
    """
    @staticmethod
    def create_rpc_server_response_size(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="rpc.server.response.size",
            description="Measures the size of RPC response messages (uncompressed).",
            unit="By",
        )


    """
    Measures the number of messages sent per RPC
    """
    @staticmethod
    def create_rpc_server_responses_per_rpc(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="rpc.server.responses_per_rpc",
            description="Measures the number of messages sent per RPC.",
            unit="{count}",
        )

