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

from logging import getLogger
from typing import Callable, Iterable, NewType, Set

from typing_extensions import final

from opentelemetry.sdk._metrics.export import AggregationTemporality, Metric

_logger = getLogger(__name__)

# TODO: make this thread safe, add Once wrappers
class MetricReader:
    def __init__(
        self,
        supported_temporalities: Iterable[AggregationTemporality] = (
            AggregationTemporality.CUMULATIVE,
        ),
        preferred_temporality: AggregationTemporality = AggregationTemporality.CUMULATIVE,
    ):
        self._shutdown = False
        self._collect: Callable[
            [AggregationTemporality], Iterable[Metric]
        ] = None
        self._supported_temporalities = set(supported_temporalities)
        self._preferred_temporality = preferred_temporality

    @final
    def collect(self):
        if self._collect is None:
            _logger.warning(
                "Can not call collect on a MetricReader until it is registered on a MeterProvider"
            )
            return []
        # TODO: temporality override rules
        return self._collect(self._preferred_temporality)

    @final
    @property
    def supported_temporalities(self) -> Set[AggregationTemporality]:
        return self._supported_temporalities

    @final
    def _set_collect_callback(
        self, func: Callable[[], Iterable[Metric]]
    ) -> None:
        """For internal use by SDK only"""
        self._collect = func

    def shutdown(self):
        # FIXME this will need a Once wrapper
        self._shutdown = True
