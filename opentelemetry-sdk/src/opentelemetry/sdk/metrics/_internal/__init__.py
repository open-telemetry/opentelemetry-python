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
from os import environ
from threading import Lock
from time import time_ns
from typing import Optional, Sequence

# This kind of import is needed to avoid Sphinx errors.
import opentelemetry.sdk.metrics
from opentelemetry.metrics import Counter as APICounter
from opentelemetry.metrics import Histogram as APIHistogram
from opentelemetry.metrics import Meter as APIMeter
from opentelemetry.metrics import MeterProvider as APIMeterProvider
from opentelemetry.metrics import NoOpMeter
from opentelemetry.metrics import ObservableCounter as APIObservableCounter
from opentelemetry.metrics import ObservableGauge as APIObservableGauge
from opentelemetry.metrics import (
    ObservableUpDownCounter as APIObservableUpDownCounter,
)
from opentelemetry.metrics import UpDownCounter as APIUpDownCounter
from opentelemetry.metrics import _Gauge as APIGauge
from opentelemetry.sdk.environment_variables import OTEL_SDK_DISABLED
from opentelemetry.sdk.metrics._internal.exceptions import MetricsTimeoutError
from opentelemetry.sdk.metrics._internal.instrument import (
    _Counter,
    _Gauge,
    _Histogram,
    _ObservableCounter,
    _ObservableGauge,
    _ObservableUpDownCounter,
    _UpDownCounter,
)
from opentelemetry.sdk.metrics._internal.measurement_consumer import (
    MeasurementConsumer,
    SynchronousMeasurementConsumer,
)
from opentelemetry.sdk.metrics._internal.sdk_configuration import (
    SdkConfiguration,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.util._once import Once

_logger = getLogger(__name__)


class Meter(APIMeter):
    """See `opentelemetry.metrics.Meter`."""

    def __init__(
        self,
        instrumentation_scope: InstrumentationScope,
        measurement_consumer: MeasurementConsumer,
    ):
        super().__init__(
            name=instrumentation_scope.name,
            version=instrumentation_scope.version,
            schema_url=instrumentation_scope.schema_url,
        )
        self._instrumentation_scope = instrumentation_scope
        self._measurement_consumer = measurement_consumer
        self._instrument_id_instrument = {}  # type: ignore[var-annotated] # <will add tracking issue num>
        self._instrument_id_instrument_lock = Lock()

    def create_counter(self, name, unit="", description="") -> APICounter:  # type: ignore[no-untyped-def] # <will add tracking issue num>

        (
            is_instrument_registered,
            instrument_id,
        ) = self._is_instrument_registered(
            name, _Counter, unit, description
        )  # type: ignore[misc] # <will add tracking issue num>

        if is_instrument_registered:
            # FIXME #2558 go through all views here and check if this
            # instrument registration conflict can be fixed. If it can be, do
            # not log the following warning.
            _logger.warning(
                "An instrument with name %s, type %s, unit %s and "
                "description %s has been created already.",
                name,  # type: ignore[misc] # <will add tracking issue num>
                APICounter.__name__,
                unit,  # type: ignore[misc] # <will add tracking issue num>
                description,  # type: ignore[misc] # <will add tracking issue num>
            )
            with self._instrument_id_instrument_lock:
                return self._instrument_id_instrument[instrument_id]  # type: ignore[misc, no-any-return] # <will add tracking issue num>

        instrument = _Counter(  # type: ignore[no-untyped-call] # <will add tracking issue num>
            name,  # type: ignore[misc] # <will add tracking issue num>
            self._instrumentation_scope,
            self._measurement_consumer,
            unit,  # type: ignore[misc] # <will add tracking issue num>
            description,  # type: ignore[misc] # <will add tracking issue num>
        )

        with self._instrument_id_instrument_lock:
            self._instrument_id_instrument[instrument_id] = instrument  # type: ignore[misc] # <will add tracking issue num>
            return instrument

    def create_up_down_counter(  # type: ignore[no-untyped-def] # <will add tracking issue num>
        self, name, unit="", description=""
    ) -> APIUpDownCounter:

        (
            is_instrument_registered,
            instrument_id,
        ) = self._is_instrument_registered(
            name, _UpDownCounter, unit, description  # type: ignore[misc] # <will add tracking issue num>
        )

        if is_instrument_registered:
            # FIXME #2558 go through all views here and check if this
            # instrument registration conflict can be fixed. If it can be, do
            # not log the following warning.
            _logger.warning(
                "An instrument with name %s, type %s, unit %s and "
                "description %s has been created already.",
                name,  # type: ignore[misc] # <will add tracking issue num>
                APIUpDownCounter.__name__,
                unit,  # type: ignore[misc] # <will add tracking issue num>
                description,  # type: ignore[misc] # <will add tracking issue num>
            )
            with self._instrument_id_instrument_lock:
                return self._instrument_id_instrument[instrument_id]  # type: ignore[misc, no-any-return] # <will add tracking issue num>

        instrument = _UpDownCounter(  # type: ignore[no-untyped-call] # <will add tracking issue num>
            name,  # type: ignore[misc] # <will add tracking issue num>
            self._instrumentation_scope,
            self._measurement_consumer,
            unit,  # type: ignore[misc] # <will add tracking issue num>
            description,  # type: ignore[misc] # <will add tracking issue num>
        )

        with self._instrument_id_instrument_lock:
            self._instrument_id_instrument[instrument_id] = instrument  # type: ignore[misc] # <will add tracking issue num>
            return instrument

    def create_observable_counter(  # type: ignore[no-untyped-def] # <will add tracking issue num>
        self, name, callbacks=None, unit="", description=""
    ) -> APIObservableCounter:

        (
            is_instrument_registered,
            instrument_id,
        ) = self._is_instrument_registered(
            name, _ObservableCounter, unit, description  # type: ignore[misc] # <will add tracking issue num>
        )

        if is_instrument_registered:
            # FIXME #2558 go through all views here and check if this
            # instrument registration conflict can be fixed. If it can be, do
            # not log the following warning.
            _logger.warning(
                "An instrument with name %s, type %s, unit %s and "
                "description %s has been created already.",
                name,  # type: ignore[misc] # <will add tracking issue num>
                APIObservableCounter.__name__,
                unit,  # type: ignore[misc] # <will add tracking issue num>
                description,  # type: ignore[misc] # <will add tracking issue num>
            )
            with self._instrument_id_instrument_lock:
                return self._instrument_id_instrument[instrument_id]  # type: ignore[misc, no-any-return] # <will add tracking issue num>

        instrument = _ObservableCounter(  # type: ignore[no-untyped-call] # <will add tracking issue num>
            name,  # type: ignore[misc] # <will add tracking issue num>
            self._instrumentation_scope,
            self._measurement_consumer,
            callbacks,  # type: ignore[misc] # <will add tracking issue num>
            unit,  # type: ignore[misc] # <will add tracking issue num>
            description,  # type: ignore[misc] # <will add tracking issue num>
        )

        self._measurement_consumer.register_asynchronous_instrument(instrument)

        with self._instrument_id_instrument_lock:
            self._instrument_id_instrument[instrument_id] = instrument  # type: ignore[misc] # <will add tracking issue num>
            return instrument

    def create_histogram(self, name, unit="", description="") -> APIHistogram:  # type: ignore[no-untyped-def] # <will add tracking issue num>

        (
            is_instrument_registered,
            instrument_id,
        ) = self._is_instrument_registered(
            name, _Histogram, unit, description
        )  # type: ignore[misc] # <will add tracking issue num>

        if is_instrument_registered:
            # FIXME #2558 go through all views here and check if this
            # instrument registration conflict can be fixed. If it can be, do
            # not log the following warning.
            _logger.warning(
                "An instrument with name %s, type %s, unit %s and "
                "description %s has been created already.",
                name,  # type: ignore[misc] # <will add tracking issue num>
                APIHistogram.__name__,
                unit,  # type: ignore[misc] # <will add tracking issue num>
                description,  # type: ignore[misc] # <will add tracking issue num>
            )
            with self._instrument_id_instrument_lock:
                return self._instrument_id_instrument[instrument_id]  # type: ignore[misc, no-any-return] # <will add tracking issue num>

        instrument = _Histogram(  # type: ignore[no-untyped-call] # <will add tracking issue num>
            name,  # type: ignore[misc] # <will add tracking issue num>
            self._instrumentation_scope,
            self._measurement_consumer,
            unit,  # type: ignore[misc] # <will add tracking issue num>
            description,  # type: ignore[misc] # <will add tracking issue num>
        )
        with self._instrument_id_instrument_lock:
            self._instrument_id_instrument[instrument_id] = instrument  # type: ignore[misc] # <will add tracking issue num>
            return instrument

    def create_gauge(self, name, unit="", description="") -> APIGauge:  # type: ignore[no-untyped-def] # <will add tracking issue num>

        (
            is_instrument_registered,
            instrument_id,
        ) = self._is_instrument_registered(
            name, _Gauge, unit, description
        )  # type: ignore[misc] # <will add tracking issue num>

        if is_instrument_registered:
            # FIXME #2558 go through all views here and check if this
            # instrument registration conflict can be fixed. If it can be, do
            # not log the following warning.
            _logger.warning(
                "An instrument with name %s, type %s, unit %s and "
                "description %s has been created already.",
                name,  # type: ignore[misc] # <will add tracking issue num>
                APIGauge.__name__,
                unit,  # type: ignore[misc] # <will add tracking issue num>
                description,  # type: ignore[misc] # <will add tracking issue num>
            )
            with self._instrument_id_instrument_lock:
                return self._instrument_id_instrument[instrument_id]  # type: ignore[misc, no-any-return] # <will add tracking issue num>

        instrument = _Gauge(  # type: ignore[no-untyped-call] # <will add tracking issue num>
            name,  # type: ignore[misc] # <will add tracking issue num>
            self._instrumentation_scope,
            self._measurement_consumer,
            unit,  # type: ignore[misc] # <will add tracking issue num>
            description,  # type: ignore[misc] # <will add tracking issue num>
        )

        with self._instrument_id_instrument_lock:
            self._instrument_id_instrument[instrument_id] = instrument  # type: ignore[misc] # <will add tracking issue num>
            return instrument

    def create_observable_gauge(  # type: ignore[no-untyped-def] # <will add tracking issue num>
        self, name, callbacks=None, unit="", description=""
    ) -> APIObservableGauge:

        (
            is_instrument_registered,
            instrument_id,
        ) = self._is_instrument_registered(
            name, _ObservableGauge, unit, description  # type: ignore[misc] # <will add tracking issue num>
        )

        if is_instrument_registered:
            # FIXME #2558 go through all views here and check if this
            # instrument registration conflict can be fixed. If it can be, do
            # not log the following warning.
            _logger.warning(
                "An instrument with name %s, type %s, unit %s and "
                "description %s has been created already.",
                name,  # type: ignore[misc] # <will add tracking issue num>
                APIObservableGauge.__name__,
                unit,  # type: ignore[misc] # <will add tracking issue num>
                description,  # type: ignore[misc] # <will add tracking issue num>
            )
            with self._instrument_id_instrument_lock:
                return self._instrument_id_instrument[instrument_id]  # type: ignore[misc, no-any-return] # <will add tracking issue num>

        instrument = _ObservableGauge(  # type: ignore[no-untyped-call] # <will add tracking issue num>
            name,  # type: ignore[misc] # <will add tracking issue num>
            self._instrumentation_scope,
            self._measurement_consumer,
            callbacks,  # type: ignore[misc] # <will add tracking issue num>
            unit,  # type: ignore[misc] # <will add tracking issue num>
            description,  # type: ignore[misc] # <will add tracking issue num>
        )

        self._measurement_consumer.register_asynchronous_instrument(instrument)

        with self._instrument_id_instrument_lock:
            self._instrument_id_instrument[instrument_id] = instrument  # type: ignore[misc] # <will add tracking issue num>
            return instrument

    def create_observable_up_down_counter(  # type: ignore[no-untyped-def] # <will add tracking issue num>
        self, name, callbacks=None, unit="", description=""
    ) -> APIObservableUpDownCounter:

        (
            is_instrument_registered,
            instrument_id,
        ) = self._is_instrument_registered(
            name, _ObservableUpDownCounter, unit, description  # type: ignore[misc] # <will add tracking issue num>
        )

        if is_instrument_registered:
            # FIXME #2558 go through all views here and check if this
            # instrument registration conflict can be fixed. If it can be, do
            # not log the following warning.
            _logger.warning(
                "An instrument with name %s, type %s, unit %s and "
                "description %s has been created already.",
                name,  # type: ignore[misc] # <will add tracking issue num>
                APIObservableUpDownCounter.__name__,
                unit,  # type: ignore[misc] # <will add tracking issue num>
                description,  # type: ignore[misc] # <will add tracking issue num>
            )
            with self._instrument_id_instrument_lock:
                return self._instrument_id_instrument[instrument_id]  # type: ignore[misc, no-any-return] # <will add tracking issue num>

        instrument = _ObservableUpDownCounter(  # type: ignore[no-untyped-call] # <will add tracking issue num>
            name,  # type: ignore[misc] # <will add tracking issue num>
            self._instrumentation_scope,
            self._measurement_consumer,
            callbacks,  # type: ignore[misc] # <will add tracking issue num>
            unit,  # type: ignore[misc] # <will add tracking issue num>
            description,  # type: ignore[misc] # <will add tracking issue num>
        )

        self._measurement_consumer.register_asynchronous_instrument(instrument)

        with self._instrument_id_instrument_lock:
            self._instrument_id_instrument[instrument_id] = instrument  # type: ignore[misc] # <will add tracking issue num>
            return instrument


class MeterProvider(APIMeterProvider):
    r"""See `opentelemetry.metrics.MeterProvider`.

    Args:
        metric_readers: Register metric readers to collect metrics from the SDK
            on demand. Each :class:`opentelemetry.sdk.metrics.export.MetricReader` is
            completely independent and will collect separate streams of
            metrics. TODO: reference ``PeriodicExportingMetricReader`` usage with push
            exporters here.
        resource: The resource representing what the metrics emitted from the SDK pertain to.
        shutdown_on_exit: If true, registers an `atexit` handler to call
            `MeterProvider.shutdown`
        views: The views to configure the metric output the SDK

    By default, instruments which do not match any :class:`opentelemetry.sdk.metrics.view.View` (or if no :class:`opentelemetry.sdk.metrics.view.View`\ s
    are provided) will report metrics with the default aggregation for the
    instrument's kind. To disable instruments by default, configure a match-all
    :class:`opentelemetry.sdk.metrics.view.View` with `DropAggregation` and then create :class:`opentelemetry.sdk.metrics.view.View`\ s to re-enable
    individual instruments:

    .. code-block:: python
        :caption: Disable default views

        MeterProvider(
            views=[
                View(instrument_name="*", aggregation=DropAggregation()),
                View(instrument_name="mycounter"),
            ],
            # ...
        )
    """

    _all_metric_readers_lock = Lock()
    _all_metric_readers = set()  # type: ignore[var-annotated] # <will add tracking issue num>

    def __init__(
        self,
        metric_readers: Sequence[  # type: ignore[name-defined] # <will add tracking issue num>
            "opentelemetry.sdk.metrics.export.MetricReader"
        ] = (),
        resource: Resource = None,  # type: ignore[assignment] # <will add tracking issue num>
        shutdown_on_exit: bool = True,
        views: Sequence["opentelemetry.sdk.metrics.view.View"] = (),  # type: ignore[name-defined] # <will add tracking issue num>
    ):
        self._lock = Lock()
        self._meter_lock = Lock()
        self._atexit_handler = None
        if resource is None:
            resource = Resource.create({})
        self._sdk_config = SdkConfiguration(
            resource=resource,
            metric_readers=metric_readers,
            views=views,
        )
        self._measurement_consumer = SynchronousMeasurementConsumer(
            sdk_config=self._sdk_config
        )
        disabled = environ.get(OTEL_SDK_DISABLED, "")
        self._disabled = disabled.lower().strip() == "true"

        if shutdown_on_exit:
            self._atexit_handler = register(self.shutdown)  # type: ignore[misc] # <will add tracking issue num>

        self._meters = {}  # type: ignore[var-annotated] # <will add tracking issue num>
        self._shutdown_once = Once()
        self._shutdown = False

        for metric_reader in self._sdk_config.metric_readers:

            with self._all_metric_readers_lock:
                if metric_reader in self._all_metric_readers:  # type: ignore[misc] # <will add tracking issue num>
                    raise Exception(
                        f"MetricReader {metric_reader} has been registered "
                        "already in other MeterProvider instance"
                    )

                self._all_metric_readers.add(metric_reader)  # type: ignore[misc] # <will add tracking issue num>

            metric_reader._set_collect_callback(
                self._measurement_consumer.collect
            )

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        deadline_ns = time_ns() + timeout_millis * 10**6

        metric_reader_error = {}

        for metric_reader in self._sdk_config.metric_readers:
            current_ts = time_ns()
            try:
                if current_ts >= deadline_ns:
                    raise MetricsTimeoutError(
                        "Timed out while flushing metric readers"
                    )
                metric_reader.force_flush(
                    timeout_millis=(deadline_ns - current_ts) / 10**6
                )

            # pylint: disable=broad-except
            except Exception as error:

                metric_reader_error[metric_reader] = error

        if metric_reader_error:

            metric_reader_error_string = "\n".join(
                [
                    f"{metric_reader.__class__.__name__}: {repr(error)}"  # type: ignore[misc] # <will add tracking issue num>
                    for metric_reader, error in metric_reader_error.items()
                ]
            )

            raise Exception(
                "MeterProvider.force_flush failed because the following "
                "metric readers failed during collect:\n"
                f"{metric_reader_error_string}"
            )
        return True

    def shutdown(self, timeout_millis: float = 30_000):  # type: ignore[no-untyped-def] # <will add tracking issue num>
        deadline_ns = time_ns() + timeout_millis * 10**6

        def _shutdown():  # type: ignore[no-untyped-def] # <will add tracking issue num>
            self._shutdown = True

        did_shutdown = self._shutdown_once.do_once(_shutdown)  # type: ignore[misc] # <will add tracking issue num>

        if not did_shutdown:
            _logger.warning("shutdown can only be called once")
            return

        metric_reader_error = {}

        for metric_reader in self._sdk_config.metric_readers:
            current_ts = time_ns()
            try:
                if current_ts >= deadline_ns:
                    raise Exception(
                        "Didn't get to execute, deadline already exceeded"
                    )
                metric_reader.shutdown(
                    timeout_millis=(deadline_ns - current_ts) / 10**6
                )

            # pylint: disable=broad-except
            except Exception as error:

                metric_reader_error[metric_reader] = error

        if self._atexit_handler is not None:  # type: ignore[misc] # <will add tracking issue num>
            unregister(self._atexit_handler)  # type: ignore[misc] # <will add tracking issue num>
            self._atexit_handler = None

        if metric_reader_error:

            metric_reader_error_string = "\n".join(
                [
                    f"{metric_reader.__class__.__name__}: {repr(error)}"  # type: ignore[misc] # <will add tracking issue num>
                    for metric_reader, error in metric_reader_error.items()
                ]
            )

            raise Exception(
                (
                    "MeterProvider.shutdown failed because the following "
                    "metric readers failed during shutdown:\n"
                    f"{metric_reader_error_string}"
                )
            )

    def get_meter(
        self,
        name: str,
        version: Optional[str] = None,
        schema_url: Optional[str] = None,
    ) -> Meter:

        if self._disabled:
            _logger.warning("SDK is disabled.")
            return NoOpMeter(name, version=version, schema_url=schema_url)  # type: ignore[return-value] # <will add tracking issue num>

        if self._shutdown:
            _logger.warning(
                "A shutdown `MeterProvider` can not provide a `Meter`"
            )
            return NoOpMeter(name, version=version, schema_url=schema_url)  # type: ignore[return-value] # <will add tracking issue num>

        if not name:
            _logger.warning("Meter name cannot be None or empty.")
            return NoOpMeter(name, version=version, schema_url=schema_url)  # type: ignore[return-value] # <will add tracking issue num>

        info = InstrumentationScope(name, version, schema_url)
        with self._meter_lock:
            if not self._meters.get(info):  # type: ignore[misc] # <will add tracking issue num>
                # FIXME #2558 pass SDKConfig object to meter so that the meter
                # has access to views.
                self._meters[info] = Meter(  # type: ignore[misc] # <will add tracking issue num>
                    info,
                    self._measurement_consumer,
                )
            return self._meters[info]  # type: ignore[misc, no-any-return] # <will add tracking issue num>
