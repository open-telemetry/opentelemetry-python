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

from atexit import register, unregister
from logging import getLogger
from threading import Lock
from typing import Optional, Sequence

from opentelemetry._metrics import Meter as APIMeter
from opentelemetry._metrics import MeterProvider as APIMeterProvider
from opentelemetry._metrics import NoOpMeter
from opentelemetry._metrics.instrument import Counter as APICounter
from opentelemetry._metrics.instrument import Histogram as APIHistogram
from opentelemetry._metrics.instrument import (
    ObservableCounter as APIObservableCounter,
)
from opentelemetry._metrics.instrument import (
    ObservableGauge as APIObservableGauge,
)
from opentelemetry._metrics.instrument import (
    ObservableUpDownCounter as APIObservableUpDownCounter,
)
from opentelemetry._metrics.instrument import UpDownCounter as APIUpDownCounter
from opentelemetry.sdk._metrics.instrument import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk._metrics.measurement_consumer import (
    MeasurementConsumer,
    SynchronousMeasurementConsumer,
)
from opentelemetry.sdk._metrics.metric_reader import MetricReader
from opentelemetry.sdk._metrics.sdk_configuration import SdkConfiguration
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo

_logger = getLogger(__name__)


class Meter(APIMeter):
    def __init__(
        self,
        instrumentation_info: InstrumentationInfo,
        measurement_consumer: MeasurementConsumer,
    ):
        super().__init__(instrumentation_info)
        self._instrumentation_info = instrumentation_info
        self._measurement_consumer = measurement_consumer

    def create_counter(self, name, unit=None, description=None) -> APICounter:
        return Counter(
            name,
            self._instrumentation_info,
            self._measurement_consumer,
            unit,
            description,
        )

    def create_up_down_counter(
        self, name, unit=None, description=None
    ) -> APIUpDownCounter:
        return UpDownCounter(
            name,
            self._instrumentation_info,
            self._measurement_consumer,
            unit,
            description,
        )

    def create_observable_counter(
        self, name, callback, unit=None, description=None
    ) -> APIObservableCounter:

        instrument = ObservableCounter(
            name,
            self._instrumentation_info,
            self._measurement_consumer,
            callback,
            unit,
            description,
        )

        self._measurement_consumer.register_asynchronous_instrument(instrument)

        return instrument

    def create_histogram(
        self, name, unit=None, description=None
    ) -> APIHistogram:
        return Histogram(
            name,
            self._instrumentation_info,
            self._measurement_consumer,
            unit,
            description,
        )

    def create_observable_gauge(
        self, name, callback, unit=None, description=None
    ) -> APIObservableGauge:

        instrument = ObservableGauge(
            name,
            self._instrumentation_info,
            self._measurement_consumer,
            callback,
            unit,
            description,
        )

        self._measurement_consumer.register_asynchronous_instrument(instrument)

        return instrument

    def create_observable_up_down_counter(
        self, name, callback, unit=None, description=None
    ) -> APIObservableUpDownCounter:

        instrument = ObservableUpDownCounter(
            name,
            self._instrumentation_info,
            self._measurement_consumer,
            callback,
            unit,
            description,
        )

        self._measurement_consumer.register_asynchronous_instrument(instrument)

        return instrument


class MeterProvider(APIMeterProvider):
    """See `opentelemetry._metrics.MeterProvider`."""

    def __init__(
        self,
        metric_readers: Sequence[MetricReader] = (),
        resource: Resource = Resource.create({}),
        shutdown_on_exit: bool = True,
    ):
        self._lock = Lock()
        self._meter_lock = Lock()
        self._atexit_handler = None
        self._sdk_config = SdkConfiguration(
            resource=resource, metric_readers=metric_readers
        )
        self._measurement_consumer = SynchronousMeasurementConsumer(
            sdk_config=self._sdk_config
        )

        if shutdown_on_exit:
            self._atexit_handler = register(self.shutdown)

        self._meters = {}
        self._metric_readers = metric_readers

        for metric_reader in self._sdk_config.metric_readers:
            metric_reader._register_measurement_consumer(self)

        self._shutdown = False

    def force_flush(self) -> bool:

        # FIXME implement a timeout

        metric_reader_result = True

        for metric_reader in self._sdk_config.metric_readers:
            metric_reader_result = (
                metric_reader_result and metric_reader.force_flush()
            )

        if not metric_reader_result:
            _logger.warning("Unable to force flush all metric readers")

        return metric_reader_result

    def shutdown(self):
        # FIXME implement a timeout

        if self._shutdown:
            _logger.warning("shutdown can only be called once")
            return False

        overall_result = True

        for metric_reader in self._sdk_config.metric_readers:
            metric_reader_result = metric_reader.shutdown()

            if not metric_reader_result:
                _logger.warning(
                    "MetricReader {metric_reader} failed to shutdown"
                )

            overall_result = overall_result and metric_reader_result

        self._shutdown = True

        if self._atexit_handler is not None:
            unregister(self._atexit_handler)
            self._atexit_handler = None

        return overall_result

    def get_meter(
        self,
        name: str,
        version: Optional[str] = None,
        schema_url: Optional[str] = None,
    ) -> Meter:

        if self._shutdown:
            _logger.warning(
                "A shutdown `MeterProvider` can not provide a `Meter`"
            )
            return NoOpMeter(name, version=version, schema_url=schema_url)

        info = InstrumentationInfo(name, version, schema_url)
        with self._meter_lock:
            if not self._meters.get(info):
                self._meters[info] = Meter(
                    info,
                    self._measurement_consumer,
                )
            return self._meters[info]
