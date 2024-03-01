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

class MessagingMetrics:

    """
    Measures the duration of deliver operation
    """
    @staticmethod
    def create_messaging_deliver_duration(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="messaging.deliver.duration",
            description="Measures the duration of deliver operation.",
            unit="s",
        )


    """
    Measures the number of delivered messages
    """
    @staticmethod
    def create_messaging_deliver_messages(meter: Meter) -> Counter:
        return meter.create_counter(
            name="messaging.deliver.messages",
            description="Measures the number of delivered messages.",
            unit="{message}",
        )


    """
    Measures the duration of publish operation
    """
    @staticmethod
    def create_messaging_publish_duration(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="messaging.publish.duration",
            description="Measures the duration of publish operation.",
            unit="s",
        )


    """
    Measures the number of published messages
    """
    @staticmethod
    def create_messaging_publish_messages(meter: Meter) -> Counter:
        return meter.create_counter(
            name="messaging.publish.messages",
            description="Measures the number of published messages.",
            unit="{message}",
        )


    """
    Measures the duration of receive operation
    """
    @staticmethod
    def create_messaging_receive_duration(meter: Meter) -> Histogram:
        return meter.create_histogram(
            name="messaging.receive.duration",
            description="Measures the duration of receive operation.",
            unit="s",
        )


    """
    Measures the number of received messages
    """
    @staticmethod
    def create_messaging_receive_messages(meter: Meter) -> Counter:
        return meter.create_counter(
            name="messaging.receive.messages",
            description="Measures the number of received messages.",
            unit="{message}",
        )
