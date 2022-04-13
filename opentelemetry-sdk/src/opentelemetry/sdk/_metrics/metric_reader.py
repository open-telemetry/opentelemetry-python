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

import logging
from abc import ABC, abstractmethod
from typing import Callable, Iterable

from typing_extensions import final

from opentelemetry.sdk._metrics.point import AggregationTemporality, Metric

_logger = logging.getLogger(__name__)


class MetricReader(ABC):
    """
    .. document protected _receive_metrics which is a intended to be overriden by subclass
    .. automethod:: _receive_metrics
    """

    def __init__(
        self,
        preferred_temporality: AggregationTemporality = AggregationTemporality.CUMULATIVE,
    ) -> None:
        self._collect: Callable[
            ["MetricReader", AggregationTemporality], Iterable[Metric]
        ] = None
        self._preferred_temporality = preferred_temporality

    @final
    def collect(self) -> None:
        """Collects the metrics from the internal SDK state and
        invokes the `_receive_metrics` with the collection.
        """
        if self._collect is None:
            _logger.warning(
                "Cannot call collect on a MetricReader until it is registered on a MeterProvider"
            )
            return
        self._receive_metrics(self._collect(self, self._preferred_temporality))

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
    def _receive_metrics(self, metrics: Iterable[Metric]):
        """Called by `MetricReader.collect` when it receives a batch of metrics"""

    @abstractmethod
    def shutdown(self):
        """Shuts down the MetricReader. This method provides a way
        for the MetricReader to do any cleanup required. A metric reader can
        only be shutdown once, any subsequent calls are ignored and return
        failure status.

        When a `MetricReader` is registered on a
        :class:`~opentelemetry.sdk._metrics.MeterProvider`,
        :meth:`~opentelemetry.sdk._metrics.MeterProvider.shutdown` will invoke this
        automatically.
        """
