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


from typing import (
    Callable,
    Final,
    Generator,
    Iterable,
    Optional,
    Sequence,
    Union,
)

from opentelemetry.metrics import (
    CallbackOptions,
    Meter,
    ObservableGauge,
    Observation,
)

# pylint: disable=invalid-name
CallbackT = Union[
    Callable[[CallbackOptions], Iterable[Observation]],
    Generator[Iterable[Observation], CallbackOptions, None],
]

NODEJS_EVENTLOOP_DELAY_MAX: Final = "nodejs.eventloop.delay.max"
"""
Event loop maximum delay
Instrument: gauge
Unit: s
Note: Value can be retrieved from value `histogram.max` of [`perf_hooks.monitorEventLoopDelay([options])`](https://nodejs.org/api/perf_hooks.html#perf_hooksmonitoreventloopdelayoptions).
"""


def create_nodejs_eventloop_delay_max(
    meter: Meter, callbacks: Optional[Sequence[CallbackT]]
) -> ObservableGauge:
    """Event loop maximum delay"""
    return meter.create_observable_gauge(
        name=NODEJS_EVENTLOOP_DELAY_MAX,
        callbacks=callbacks,
        description="Event loop maximum delay.",
        unit="s",
    )


NODEJS_EVENTLOOP_DELAY_MEAN: Final = "nodejs.eventloop.delay.mean"
"""
Event loop mean delay
Instrument: gauge
Unit: s
Note: Value can be retrieved from value `histogram.mean` of [`perf_hooks.monitorEventLoopDelay([options])`](https://nodejs.org/api/perf_hooks.html#perf_hooksmonitoreventloopdelayoptions).
"""


def create_nodejs_eventloop_delay_mean(
    meter: Meter, callbacks: Optional[Sequence[CallbackT]]
) -> ObservableGauge:
    """Event loop mean delay"""
    return meter.create_observable_gauge(
        name=NODEJS_EVENTLOOP_DELAY_MEAN,
        callbacks=callbacks,
        description="Event loop mean delay.",
        unit="s",
    )


NODEJS_EVENTLOOP_DELAY_MIN: Final = "nodejs.eventloop.delay.min"
"""
Event loop minimum delay
Instrument: gauge
Unit: s
Note: Value can be retrieved from value `histogram.min` of [`perf_hooks.monitorEventLoopDelay([options])`](https://nodejs.org/api/perf_hooks.html#perf_hooksmonitoreventloopdelayoptions).
"""


def create_nodejs_eventloop_delay_min(
    meter: Meter, callbacks: Optional[Sequence[CallbackT]]
) -> ObservableGauge:
    """Event loop minimum delay"""
    return meter.create_observable_gauge(
        name=NODEJS_EVENTLOOP_DELAY_MIN,
        callbacks=callbacks,
        description="Event loop minimum delay.",
        unit="s",
    )


NODEJS_EVENTLOOP_DELAY_P50: Final = "nodejs.eventloop.delay.p50"
"""
Event loop 50 percentile delay
Instrument: gauge
Unit: s
Note: Value can be retrieved from value `histogram.percentile(50)` of [`perf_hooks.monitorEventLoopDelay([options])`](https://nodejs.org/api/perf_hooks.html#perf_hooksmonitoreventloopdelayoptions).
"""


def create_nodejs_eventloop_delay_p50(
    meter: Meter, callbacks: Optional[Sequence[CallbackT]]
) -> ObservableGauge:
    """Event loop 50 percentile delay"""
    return meter.create_observable_gauge(
        name=NODEJS_EVENTLOOP_DELAY_P50,
        callbacks=callbacks,
        description="Event loop 50 percentile delay.",
        unit="s",
    )


NODEJS_EVENTLOOP_DELAY_P90: Final = "nodejs.eventloop.delay.p90"
"""
Event loop 90 percentile delay
Instrument: gauge
Unit: s
Note: Value can be retrieved from value `histogram.percentile(90)` of [`perf_hooks.monitorEventLoopDelay([options])`](https://nodejs.org/api/perf_hooks.html#perf_hooksmonitoreventloopdelayoptions).
"""


def create_nodejs_eventloop_delay_p90(
    meter: Meter, callbacks: Optional[Sequence[CallbackT]]
) -> ObservableGauge:
    """Event loop 90 percentile delay"""
    return meter.create_observable_gauge(
        name=NODEJS_EVENTLOOP_DELAY_P90,
        callbacks=callbacks,
        description="Event loop 90 percentile delay.",
        unit="s",
    )


NODEJS_EVENTLOOP_DELAY_P99: Final = "nodejs.eventloop.delay.p99"
"""
Event loop 99 percentile delay
Instrument: gauge
Unit: s
Note: Value can be retrieved from value `histogram.percentile(99)` of [`perf_hooks.monitorEventLoopDelay([options])`](https://nodejs.org/api/perf_hooks.html#perf_hooksmonitoreventloopdelayoptions).
"""


def create_nodejs_eventloop_delay_p99(
    meter: Meter, callbacks: Optional[Sequence[CallbackT]]
) -> ObservableGauge:
    """Event loop 99 percentile delay"""
    return meter.create_observable_gauge(
        name=NODEJS_EVENTLOOP_DELAY_P99,
        callbacks=callbacks,
        description="Event loop 99 percentile delay.",
        unit="s",
    )


NODEJS_EVENTLOOP_DELAY_STDDEV: Final = "nodejs.eventloop.delay.stddev"
"""
Event loop standard deviation delay
Instrument: gauge
Unit: s
Note: Value can be retrieved from value `histogram.stddev` of [`perf_hooks.monitorEventLoopDelay([options])`](https://nodejs.org/api/perf_hooks.html#perf_hooksmonitoreventloopdelayoptions).
"""


def create_nodejs_eventloop_delay_stddev(
    meter: Meter, callbacks: Optional[Sequence[CallbackT]]
) -> ObservableGauge:
    """Event loop standard deviation delay"""
    return meter.create_observable_gauge(
        name=NODEJS_EVENTLOOP_DELAY_STDDEV,
        callbacks=callbacks,
        description="Event loop standard deviation delay.",
        unit="s",
    )


NODEJS_EVENTLOOP_UTILIZATION: Final = "nodejs.eventloop.utilization"
"""
Event loop utilization
Instrument: gauge
Unit: 1
Note: The value range is [0.0,1.0] and can be retrieved from value [`performance.eventLoopUtilization([utilization1[, utilization2]])`](https://nodejs.org/api/perf_hooks.html#performanceeventlooputilizationutilization1-utilization2).
"""


def create_nodejs_eventloop_utilization(
    meter: Meter, callbacks: Optional[Sequence[CallbackT]]
) -> ObservableGauge:
    """Event loop utilization"""
    return meter.create_observable_gauge(
        name=NODEJS_EVENTLOOP_UTILIZATION,
        callbacks=callbacks,
        description="Event loop utilization.",
        unit="1",
    )
