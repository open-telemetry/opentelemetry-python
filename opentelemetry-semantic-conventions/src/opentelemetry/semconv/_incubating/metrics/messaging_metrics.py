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


from typing import Final

from opentelemetry.metrics import Counter, Histogram, Meter

MESSAGING_PROCESS_DURATION: Final = "messaging.process.duration"
"""
Measures the duration of process operation
Instrument: histogram
Unit: s
"""


def create_messaging_process_duration(meter: Meter) -> Histogram:
    """Measures the duration of process operation"""
    return meter.create_histogram(
        name=MESSAGING_PROCESS_DURATION,
        description="Measures the duration of process operation.",
        unit="s",
    )


MESSAGING_PROCESS_MESSAGES: Final = "messaging.process.messages"
"""
Measures the number of processed messages
Instrument: counter
Unit: {message}
"""


def create_messaging_process_messages(meter: Meter) -> Counter:
    """Measures the number of processed messages"""
    return meter.create_counter(
        name=MESSAGING_PROCESS_MESSAGES,
        description="Measures the number of processed messages.",
        unit="{message}",
    )


MESSAGING_PUBLISH_DURATION: Final = "messaging.publish.duration"
"""
Measures the duration of publish operation
Instrument: histogram
Unit: s
"""


def create_messaging_publish_duration(meter: Meter) -> Histogram:
    """Measures the duration of publish operation"""
    return meter.create_histogram(
        name=MESSAGING_PUBLISH_DURATION,
        description="Measures the duration of publish operation.",
        unit="s",
    )


MESSAGING_PUBLISH_MESSAGES: Final = "messaging.publish.messages"
"""
Measures the number of published messages
Instrument: counter
Unit: {message}
"""


def create_messaging_publish_messages(meter: Meter) -> Counter:
    """Measures the number of published messages"""
    return meter.create_counter(
        name=MESSAGING_PUBLISH_MESSAGES,
        description="Measures the number of published messages.",
        unit="{message}",
    )


MESSAGING_RECEIVE_DURATION: Final = "messaging.receive.duration"
"""
Measures the duration of receive operation
Instrument: histogram
Unit: s
"""


def create_messaging_receive_duration(meter: Meter) -> Histogram:
    """Measures the duration of receive operation"""
    return meter.create_histogram(
        name=MESSAGING_RECEIVE_DURATION,
        description="Measures the duration of receive operation.",
        unit="s",
    )


MESSAGING_RECEIVE_MESSAGES: Final = "messaging.receive.messages"
"""
Measures the number of received messages
Instrument: counter
Unit: {message}
"""


def create_messaging_receive_messages(meter: Meter) -> Counter:
    """Measures the number of received messages"""
    return meter.create_counter(
        name=MESSAGING_RECEIVE_MESSAGES,
        description="Measures the number of received messages.",
        unit="{message}",
    )
