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

from atexit import register
from logging import getLogger
from typing import Optional

from opentelemetry.metrics import Meter, MeterProvider
from opentelemetry.metrics.instrument import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk.metrics.api import MetricExporter, MetricReader, View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo

_logger = getLogger(__name__)


class Meter(Meter):
    def __init__(self, instrumentation_info: InstrumentationInfo):
        super().__init__(instrumentation_info)
        self._instrumentation_info = instrumentation_info
        self._meter_provider = None

    def create_counter(self, name, unit=None, description=None) -> Counter:
        # FIXME implement this method
        pass

    def create_up_down_counter(
        self, name, unit=None, description=None
    ) -> UpDownCounter:
        # FIXME implement this method
        pass

    def create_observable_counter(
        self, name, callback, unit=None, description=None
    ) -> ObservableCounter:
        # FIXME implement this method
        pass

    def create_histogram(self, name, unit=None, description=None) -> Histogram:
        # FIXME implement this method
        pass

    def create_observable_gauge(
        self, name, callback, unit=None, description=None
    ) -> ObservableGauge:
        # FIXME implement this method
        pass

    def create_observable_up_down_counter(
        self, name, callback, unit=None, description=None
    ) -> ObservableUpDownCounter:
        # FIXME implement this method
        pass


class MeterProvider(MeterProvider):
    """See `opentelemetry.metrics.MeterProvider`."""

    def __init__(
        self,
        resource: Resource = Resource.create({}),
        shutdown_on_exit: bool = True,
    ):
        self._resource = resource
        self._atexit_handler = None

        if shutdown_on_exit:
            self._atexit_handler = register(self.shutdown)

        self._metric_readers = []
        self._metric_exporters = []
        self._views = []
        self._shutdown = False

    @property
    def metric_readers(self):
        return self._metric_readers

    @property
    def metric_exporters(self):
        return self._metric_exporters

    @property
    def views(self):
        return self._views

    @property
    def resource(self) -> Resource:
        return self._resource

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
            return

        meter = Meter(InstrumentationInfo(name, version, schema_url))

        meter._meter_provider = self  # pylint: disable=protected-access

        return meter

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

        return result

    def force_flush(self) -> bool:
        result = True

        for metric_reader in self._metric_readers:
            result = result and metric_reader.force_flush()

        for metric_exporter in self._metric_exporters:
            result = result and metric_exporter.force_flush()

        return result

    def register_metric_reader(self, metric_reader: "MetricReader") -> None:
        self._metric_readers.append(metric_reader)

    def register_metric_exporter(
        self, metric_exporter: "MetricExporter"
    ) -> None:
        self._metric_exporters.append(metric_exporter)

    def register_view(self, view: "View") -> None:
        self._views.append(view)


class MetricReader(MetricReader):
    def collect(self):
        pass


class MetricExporter(MetricExporter):
    def export(self):
        pass


class View(View):
    pass
