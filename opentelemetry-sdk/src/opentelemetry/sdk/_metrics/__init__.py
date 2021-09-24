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

# pylint: disable=protected-access

from abc import ABC, abstractmethod
from atexit import register, unregister
from logging import getLogger
from typing import Optional

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
from opentelemetry._metrics.instrument import Synchronous
from opentelemetry._metrics.instrument import UpDownCounter as APIUpDownCounter
from opentelemetry.sdk._metrics.instrument import (
    Counter,
    Histogram,
    ObservableCounter,
    UpDownCounter,
    _ViewInstrument,
)
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

    def _initialize_instrument(self, instrument):

        for view in self._meter_provider._views:

            if view._matches_instrument(instrument):

                instrument._view_instruments.append(
                    _ViewInstrument(
                        view._name or instrument._name,
                        view._unit or instrument._unit,
                        view._description or instrument._description,
                        view._attribute_keys,
                        (
                            view._extra_dimensions
                            if isinstance(instrument, Synchronous)
                            else None
                        ),
                        view._aggregation or instrument._default_aggregation,
                        view._exemplar_reservoir,
                    )
                )

    def create_counter(self, name, unit=None, description=None) -> APICounter:
        return self._initialize_instrument(
            Counter(name, unit=unit, description=description)
        )

    def create_up_down_counter(
        self, name, unit=None, description=None
    ) -> APIUpDownCounter:
        return self._initialize_instrument(
            UpDownCounter(name, unit=unit, description=description)
        )

    def create_observable_counter(
        self, name, callback, unit=None, description=None
    ) -> APIObservableCounter:
        return self._initialize_instrument(
            ObservableCounter(name, unit=unit, description=description)
        )

    def create_histogram(
        self, name, unit=None, description=None
    ) -> APIHistogram:
        return self._initialize_instrument(
            Histogram(name, unit=unit, description=description)
        )

    def create_observable_gauge(
        self, name, callback, unit=None, description=None
    ) -> APIObservableGauge:
        # FIXME implement this method
        pass

    def create_observable_up_down_counter(
        self, name, callback, unit=None, description=None
    ) -> APIObservableUpDownCounter:
        # FIXME implement this method
        pass


class MeterProvider(APIMeterProvider):
    """See `opentelemetry._metrics.MeterProvider`."""

    def __init__(
        self,
        resource: Resource = Resource.create({}),
        shutdown_on_exit: bool = True,
        views=None,
        use_always_matching_view=True,
    ):
        self._resource = resource
        self._atexit_handler = None

        if shutdown_on_exit:
            self._atexit_handler = register(self.shutdown)

        self._metric_readers = []
        self._metric_exporters = []

        if views is None:
            self._views = []

        else:
            self._views = views

        if use_always_matching_view:
            self._views.append(View(instrument_name=".*"))

        self._shutdown = False

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

    def register_metric_reader(self, metric_reader: "MetricReader") -> None:
        # FIXME protect this method against race conditions
        self._metric_readers.append(metric_reader)

    def register_metric_exporter(
        self, metric_exporter: "MetricExporter"
    ) -> None:
        # FIXME protect this method against race conditions
        self._metric_exporters.append(metric_exporter)


class MetricReader(ABC):
    def __init__(self):
        self._shutdown = False

    @abstractmethod
    def collect(self):
        pass

    def shutdown(self):
        # FIXME this will need a Once wrapper
        self._shutdown = True


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


class SDKMetricReader(MetricReader):
    def collect(self):
        pass
