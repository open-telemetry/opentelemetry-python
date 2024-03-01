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

class AspnetcoreMetrics:

    """
    Number of exceptions caught by exception handling middleware
    """
    @staticmethod
    def create_aspnetcore_diagnostics_exceptions(meter: Meter) -> Counter:
        return meter.create_counter(
            name="aspnetcore.diagnostics.exceptions",
            description="Number of exceptions caught by exception handling middleware.",
            unit="{exception}",
        )


    """
    Number of requests that are currently active on the server that hold a rate limiting lease
    """
    @staticmethod
    def create_aspnetcore_rate_limiting_active_request_leases(meter: Meter) -> UpDownCounter:
        return meter.create_up_down_counter(
            name="aspnetcore.rate_limiting.active_request_leases",
            description="Number of requests that are currently active on the server that hold a rate limiting lease.",
            unit="{request}",
        )


    """
    Number of requests that are currently queued, waiting to acquire a rate limiting lease
    """
    @staticmethod
    def create_aspnetcore_rate_limiting_queued_requests(meter: Meter) -> UpDownCounter:
        return meter.create_up_down_counter(
            name="aspnetcore.rate_limiting.queued_requests",
            description="Number of requests that are currently queued, waiting to acquire a rate limiting lease.",
            unit="{request}",
        )


    """
    The time the request spent in a queue waiting to acquire a rate limiting lease
    """
    @staticmethod
    def create_aspnetcore_rate_limiting_request_time_in_queue(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="aspnetcore.rate_limiting.request.time_in_queue",
            description="The time the request spent in a queue waiting to acquire a rate limiting lease.",
            unit="s",
        )


    """
    The duration of rate limiting lease held by requests on the server
    """
    @staticmethod
    def create_aspnetcore_rate_limiting_request_lease_duration(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="aspnetcore.rate_limiting.request_lease.duration",
            description="The duration of rate limiting lease held by requests on the server.",
            unit="s",
        )


    """
    Number of requests that tried to acquire a rate limiting lease
    """
    @staticmethod
    def create_aspnetcore_rate_limiting_requests(meter: Meter) -> Counter:
        return meter.create_counter(
            name="aspnetcore.rate_limiting.requests",
            description="Number of requests that tried to acquire a rate limiting lease.",
            unit="{request}",
        )


    """
    Number of requests that were attempted to be matched to an endpoint
    """
    @staticmethod
    def create_aspnetcore_routing_match_attempts(meter: Meter) -> Counter:
        return meter.create_counter(
            name="aspnetcore.routing.match_attempts",
            description="Number of requests that were attempted to be matched to an endpoint.",
            unit="{match_attempt}",
        )
