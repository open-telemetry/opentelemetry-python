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

class FaasMetrics:

    """
    Number of invocation cold starts
    """
    @staticmethod
    def create_faas_coldstarts(meter: Meter) -> Counter:
        return meter.create_counter(
            name="faas.coldstarts",
            description="Number of invocation cold starts",
            unit="{coldstart}",
        )


    """
    Distribution of CPU usage per invocation
    """
    @staticmethod
    def create_faas_cpu_usage(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="faas.cpu_usage",
            description="Distribution of CPU usage per invocation",
            unit="s",
        )


    """
    Number of invocation errors
    """
    @staticmethod
    def create_faas_errors(meter: Meter) -> Counter:
        return meter.create_counter(
            name="faas.errors",
            description="Number of invocation errors",
            unit="{error}",
        )


    """
    Measures the duration of the function's initialization, such as a cold start
    """
    @staticmethod
    def create_faas_init_duration(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="faas.init_duration",
            description="Measures the duration of the function's initialization, such as a cold start",
            unit="s",
        )


    """
    Number of successful invocations
    """
    @staticmethod
    def create_faas_invocations(meter: Meter) -> Counter:
        return meter.create_counter(
            name="faas.invocations",
            description="Number of successful invocations",
            unit="{invocation}",
        )


    """
    Measures the duration of the function's logic execution
    """
    @staticmethod
    def create_faas_invoke_duration(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="faas.invoke_duration",
            description="Measures the duration of the function's logic execution",
            unit="s",
        )


    """
    Distribution of max memory usage per invocation
    """
    @staticmethod
    def create_faas_mem_usage(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="faas.mem_usage",
            description="Distribution of max memory usage per invocation",
            unit="By",
        )


    """
    Distribution of net I/O usage per invocation
    """
    @staticmethod
    def create_faas_net_io(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="faas.net_io",
            description="Distribution of net I/O usage per invocation",
            unit="By",
        )


    """
    Number of invocation timeouts
    """
    @staticmethod
    def create_faas_timeouts(meter: Meter) -> Counter:
        return meter.create_counter(
            name="faas.timeouts",
            description="Number of invocation timeouts",
            unit="{timeout}",
        )
