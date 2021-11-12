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

# pylint: disable=function-redefined,too-many-ancestors

from abc import ABC, abstractmethod
from atexit import register, unregister
from functools import partial, partialmethod
from logging import getLogger
from typing import Iterable, Optional, Sequence

from opentelemetry._metrics import Meter as APIMeter
from opentelemetry._metrics import MeterProvider as APIMeterProvider
from opentelemetry._metrics import _DefaultMeter
from opentelemetry._metrics.instrument import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk._metrics._internal import instrument as sdkinstrument
from opentelemetry.sdk._metrics._internal.measurement import (
    Measurement,
    SendMeasurementT,
)
from opentelemetry.sdk._metrics._internal.metric_processor import (
    DefaultMetricProcessor,
    MetricProcessor,
    SdkConfiguration,
)
from opentelemetry.sdk._metrics._internal.metric_reader import MetricReader
from opentelemetry.sdk._metrics.export import Metric
from opentelemetry.sdk._metrics.view import View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo

_logger = getLogger(__name__)


class Meter(APIMeter):
    def __init__(
        self,
        instrumentation_info: InstrumentationInfo,
        metric_processor: MetricProcessor,
    ):
        super().__init__(instrumentation_info)
        self._instrumentation_info = instrumentation_info
        self._metric_processor = metric_processor

    def create_counter(self, name, unit=None, description=None) -> Counter:
        return sdkinstrument.Counter(
            name,
            unit=unit,
            description=description,
            instrumentation_info=self._instrumentation_info,
            send_measurement=self._metric_processor.consume_measurement,
        )

    def create_up_down_counter(
        self, name, unit=None, description=None
    ) -> UpDownCounter:
        # FIXME implement this method
        pass

    def create_observable_counter(
        self, name, callback, unit=None, description=None
    ) -> ObservableCounter:
        instrument = sdkinstrument.ObservableCounter(
            name,
            unit,
            description,
            callback,
            instrumentation_info=self._instrumentation_info,
        )
        self._metric_processor.register_async_instrument(instrument)
        return instrument

    def create_histogram(self, name, unit=None, description=None) -> Histogram:
        # FIXME implement this method
        pass

    def create_observable_gauge(
        self, name, callback, unit=None, description=None
    ) -> ObservableGauge:
        instrument = sdkinstrument.ObservableGauge(
            name,
            unit,
            description,
            callback,
            instrumentation_info=self._instrumentation_info,
        )
        self._metric_processor.register_async_instrument(instrument)
        return instrument

    def create_observable_up_down_counter(
        self, name, callback, unit=None, description=None
    ) -> ObservableUpDownCounter:
        # FIXME implement this method
        pass


class MeterProvider(APIMeterProvider):
    """See `opentelemetry._metrics.MeterProvider`."""

    def __init__(
        self,
        *,
        metric_readers: Sequence[MetricReader],
        resource: Resource = Resource.create({}),
        views: Sequence[View] = (),
        shutdown_on_exit: bool = True,
    ):
        self._resource = resource
        self._views = views
        self._atexit_handler = None

        if shutdown_on_exit:
            self._atexit_handler = register(self.shutdown)

        self._metric_readers = metric_readers
        self._metric_exporters = []
        self._shutdown = False

        self._metric_processor = DefaultMetricProcessor(
            SdkConfiguration(
                resource=self._resource,
                views=self._views,
                metric_readers=self._metric_readers,
            )
        )

        # bind readers to collection function
        for metric_reader in self._metric_readers:
            metric_reader._set_collect_callback(
                partial(self._metric_processor.collect, metric_reader)
            )

    def get_meter(
        self,
        name: str,
        version: Optional[str] = None,
        schema_url: Optional[str] = None,
    ) -> APIMeter:

        if self._shutdown:
            _logger.warning(
                "A shutdown `MeterProvider` can not provide a `Meter`"
            )
            return _DefaultMeter(name, version=version, schema_url=schema_url)

        return Meter(
            InstrumentationInfo(name, version, schema_url),
            self._metric_processor,
        )

    def shutdown(self):
        # FIXME implement a timeout

        if self._shutdown:
            _logger.warning("shutdown can only be called once")
            return False

        result = True

        for metric_reader in self._metric_readers:
            result = result and metric_reader.shutdown()

        for metric_exporter in self._metric_exporters:
            result = result and metric_exporter.shutdown()

        self._shutdown = True

        if self._atexit_handler is not None:
            unregister(self._atexit_handler)
            self._atexit_handler = None

        return result

    def force_flush(self) -> bool:

        # FIXME implement a timeout

        metric_reader_result = True
        metric_exporter_result = True

        for metric_reader in self._metric_readers:
            metric_reader_result = (
                metric_reader_result and metric_reader.force_flush()
            )

        if not metric_reader_result:
            _logger.warning("Unable to force flush all metric readers")

        for metric_exporter in self._metric_exporters:
            metric_exporter_result = (
                metric_exporter_result and metric_exporter.force_flush()
            )

        if not metric_exporter_result:
            _logger.warning("Unable to force flush all metric exporters")

        return metric_reader_result and metric_exporter_result

    def register_metric_exporter(
        self, metric_exporter: "MetricExporter"
    ) -> None:
        # FIXME protect this method against race conditions
        self._metric_exporters.append(metric_exporter)

    def _receive_measurements(self, measurement: Measurement) -> None:
        """All instruments send measurements to this function"""
        pass


class MetricExporter(ABC):
    def __init__(self):
        self._shutdown = False

    @abstractmethod
    def export(self):
        pass

    def shutdown(self):
        # FIXME this will need a Once wrapper
        self._shutdown = True


class ConsoleMetricExporter(MetricExporter):
    def export(self):
        pass
