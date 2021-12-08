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
from opentelemetry._metrics import _DefaultMeter
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
from opentelemetry.sdk._metrics.metric_exporter import MetricExporter
from opentelemetry.sdk._metrics.metric_reader import MetricReader
from opentelemetry.sdk._metrics.view import View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo

_logger = getLogger(__name__)


class Meter(APIMeter):
    def __init__(
        self,
        instrumentation_info: InstrumentationInfo,
        meter_provider: APIMeterProvider,
    ):
        super().__init__(instrumentation_info)
        self._instrumentation_info = instrumentation_info
        self._meter_provider = meter_provider

    def create_counter(self, name, unit=None, description=None) -> APICounter:
        # pylint: disable=protected-access
        return self._meter_provider._create_counter(
            self._instrumentation_info, name, unit, description
        )

    def create_up_down_counter(
        self, name, unit=None, description=None
    ) -> APIUpDownCounter:
        # pylint: disable=protected-access
        return self._meter_provider._create_up_down_counter(
            self._instrumentation_info, name, unit, description
        )

    def create_observable_counter(
        self, name, callback, unit=None, description=None
    ) -> APIObservableCounter:
        # pylint: disable=protected-access
        return self._meter_provider._create_observable_counter(
            self._instrumentation_info, name, unit, description
        )

    def create_histogram(
        self, name, unit=None, description=None
    ) -> APIHistogram:
        # pylint: disable=protected-access
        return self._meter_provider._create_histogram(
            self._instrumentation_info, name, unit, description
        )

    def create_observable_gauge(
        self, name, callback, unit=None, description=None
    ) -> APIObservableGauge:
        # pylint: disable=protected-access
        return self._meter_provider._create_observable_gauge(
            self._instrumentation_info, name, unit, description
        )

    def create_observable_up_down_counter(
        self, name, callback, unit=None, description=None
    ) -> APIObservableUpDownCounter:
        # pylint: disable=protected-access
        return self._meter_provider._create_observable_up_down_counter(
            self._instrumentation_info, name, unit, description
        )


class MeterProvider(APIMeterProvider):
    """See `opentelemetry._metrics.MeterProvider`."""

    def __init__(
        self,
        metric_exporters: Sequence[MetricExporter] = (),
        metric_readers: Sequence[MetricReader] = (),
        views: Sequence[View] = (),
        resource: Resource = Resource.create({}),
        shutdown_on_exit: bool = True,
        use_always_matching_view: bool = True,
    ):
        self._lock = Lock()
        self._atexit_handler = None
        self.__use_always_matching_view = use_always_matching_view

        if shutdown_on_exit:
            self._atexit_handler = register(self.shutdown)

        self.__metric_readers = metric_readers

        for metric_reader in self._metric_readers:
            metric_reader._register_meter_provider(self)

        self.__metric_exporters = metric_exporters

        self.__views = views

        if self.__use_always_matching_view:
            self.__views = [*self.__views, View(instrument_name="*")]

        self.__resource = resource
        self._shutdown = False
        self.__asynchronous_instruments = []

    @property
    def _metric_readers(self):
        return self.__metric_readers

    @property
    def _use_always_matching_view(self):
        return self.__use_always_matching_view

    @property
    def _resource(self):
        return self.__resource

    @property
    def _metric_exporters(self):
        return self.__metric_exporters

    @property
    def _views(self):
        return self.__views

    @property
    def _asynchronous_instruments(self):
        return self.__asynchronous_instruments

    def _create_counter(  # pylint: disable=no-self-use
        self, instrumentation_info, name, unit, description
    ) -> APICounter:
        return Counter(instrumentation_info, name, unit, description)

    def _create_up_down_counter(  # pylint: disable=no-self-use
        self, instrumentation_info, name, unit, description
    ) -> APIUpDownCounter:
        return UpDownCounter(instrumentation_info, name, unit, description)

    def _create_observable_counter(
        self, instrumentation_info, name, unit, description
    ) -> APIObservableCounter:
        instrument = ObservableCounter(
            instrumentation_info, name, unit, description
        )

        with self._lock:
            self.__asynchronous_instruments.append(instrument)

        return instrument

    def _create_histogram(  # pylint: disable=no-self-use
        self, instrumentation_info, name, unit, description
    ) -> APIHistogram:
        return Histogram(instrumentation_info, name, unit, description)

    def _create_observable_gauge(
        self, instrumentation_info, name, unit, description
    ) -> ObservableGauge:
        instrument = ObservableGauge(
            instrumentation_info, name, unit, description
        )

        with self._lock:
            self.__asynchronous_instruments.append(instrument)

        return instrument

    def _create_observable_up_down_counter(
        self, instrumentation_info, name, unit, description
    ) -> ObservableUpDownCounter:
        instrument = ObservableUpDownCounter(
            instrumentation_info, name, unit, description
        )

        with self._lock:
            self.__asynchronous_instruments.append(instrument)

        return instrument

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
            return _DefaultMeter(name, version=version, schema_url=schema_url)

        return Meter(InstrumentationInfo(name, version, schema_url), self)
