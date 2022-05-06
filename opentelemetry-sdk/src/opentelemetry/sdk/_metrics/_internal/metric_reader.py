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

from abc import ABC, abstractmethod
from logging import getLogger
from os import environ
from typing import Callable, Dict, Iterable

from typing_extensions import final

from opentelemetry.sdk._metrics.aggregation import (
    Aggregation,
    DefaultAggregation,
)
from opentelemetry.sdk._metrics.instrument import (
    Counter,
    Histogram,
    ObservableCounter,
    ObservableGauge,
    ObservableUpDownCounter,
    UpDownCounter,
)
from opentelemetry.sdk._metrics.point import AggregationTemporality, Metric
from opentelemetry.sdk.environment_variables import (
    _OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
)

_logger = getLogger(__name__)


class MetricReader(ABC):
    """
    Base class for all metric readers

    Args:
        preferred_temporality: A mapping between instrument classes and
            aggregation temporality. By default uses CUMULATIVE for all instrument
            classes. This mapping will be used to define the default aggregation
            temporality of every instrument class. If the user wants to make a
            change in the default aggregation temporality of an instrument class,
            it is enough to pass here a dictionary whose keys are the instrument
            classes and the values are the corresponding desired aggregation
            temporalities of the classes that the user wants to change, not all of
            them. The classes not included in the passed dictionary will retain
            their association to their default aggregation temporalities.
            The value passed here will override the corresponding values set
            via the environment variable
        preferred_aggregation: A mapping between instrument classes and
            aggregation instances. By default maps all instrument classes to an
            instance of `DefaultAggregation`. This mapping will be used to
            define the default aggregation of every instrument class. If the
            user wants to make a change in the default aggregation of an
            instrument class, it is enough to pass here a dictionary whose keys
            are the instrument classes and the values are the corresponding
            desired aggregation for the instrument classes that the user wants
            to change, not necessarily all of them. The classes not included in
            the passed dictionary will retain their association to their
            default aggregations. The aggregation defined here will be
            overriden by an aggregation defined by a view that is not
            `DefaultAggregation`.

    .. document protected _receive_metrics which is a intended to be overriden by subclass
    .. automethod:: _receive_metrics
    """

    # FIXME add :std:envvar:`OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE`
    # to the end of the documentation paragraph above.

    def __init__(
        self,
        preferred_temporality: Dict[type, AggregationTemporality] = None,
        preferred_aggregation: Dict[type, Aggregation] = None,
    ) -> None:
        self._collect: Callable[
            ["MetricReader", AggregationTemporality], Iterable[Metric]
        ] = None

        if (
            environ.get(
                _OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE,
                "CUMULATIVE",
            )
            .upper()
            .strip()
            == "DELTA"
        ):
            self._instrument_class_temporality = {
                Counter: AggregationTemporality.DELTA,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.DELTA,
                ObservableCounter: AggregationTemporality.DELTA,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }

        else:
            self._instrument_class_temporality = {
                Counter: AggregationTemporality.CUMULATIVE,
                UpDownCounter: AggregationTemporality.CUMULATIVE,
                Histogram: AggregationTemporality.CUMULATIVE,
                ObservableCounter: AggregationTemporality.CUMULATIVE,
                ObservableUpDownCounter: AggregationTemporality.CUMULATIVE,
                ObservableGauge: AggregationTemporality.CUMULATIVE,
            }

        if preferred_temporality is not None:
            for temporality in preferred_temporality.values():
                if temporality not in (
                    AggregationTemporality.CUMULATIVE,
                    AggregationTemporality.DELTA,
                ):
                    raise Exception(
                        f"Invalid temporality value found {temporality}"
                    )

        self._instrument_class_temporality.update(preferred_temporality or {})
        self._preferred_temporality = preferred_temporality
        self._instrument_class_aggregation = {
            Counter: DefaultAggregation(),
            UpDownCounter: DefaultAggregation(),
            Histogram: DefaultAggregation(),
            ObservableCounter: DefaultAggregation(),
            ObservableUpDownCounter: DefaultAggregation(),
            ObservableGauge: DefaultAggregation(),
        }

        self._instrument_class_aggregation.update(preferred_aggregation or {})

    @final
    def collect(self, timeout_millis: float = 10_000) -> None:
        """Collects the metrics from the internal SDK state and
        invokes the `_receive_metrics` with the collection.
        """
        if self._collect is None:
            _logger.warning(
                "Cannot call collect on a MetricReader until it is registered on a MeterProvider"
            )
            return
        self._receive_metrics(
            self._collect(self, self._instrument_class_temporality),
            timeout_millis=timeout_millis,
        )

    @final
    def _set_collect_callback(
        self,
        func: Callable[
            ["MetricReader", AggregationTemporality], Iterable[Metric]
        ],
    ) -> None:
        """This function is internal to the SDK. It should not be called or overriden by users"""
        self._collect = func

    @abstractmethod
    def _receive_metrics(
        self,
        metrics: Iterable[Metric],
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> None:
        """Called by `MetricReader.collect` when it receives a batch of metrics"""

    @abstractmethod
    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        """Shuts down the MetricReader. This method provides a way
        for the MetricReader to do any cleanup required. A metric reader can
        only be shutdown once, any subsequent calls are ignored and return
        failure status.

        When a `MetricReader` is registered on a
        :class:`~opentelemetry.sdk._metrics.MeterProvider`,
        :meth:`~opentelemetry.sdk._metrics.MeterProvider.shutdown` will invoke this
        automatically.
        """
