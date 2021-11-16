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
from collections import OrderedDict
from logging import getLogger
from math import inf

from opentelemetry._metrics.instrument import _Monotonic
from opentelemetry.util._time import _time_ns

_logger = getLogger(__name__)


class Aggregation(ABC):
    @property
    def value(self):
        return self._value  # pylint: disable=no-member

    @abstractmethod
    def aggregate(self, value):
        pass


class NoneAggregation(Aggregation):
    """
    This aggregation drops all instrument measurements.
    """

    def __init__(self, instrument):
        self._value = None

    def aggregate(self, value):
        pass


class SumAggregation(Aggregation):
    """
    This aggregation collects data for the SDK sum metric point.
    """

    def __init__(self, instrument):
        self._value = 0

    def aggregate(self, value):
        self._value = self._value + value


class LastValueAggregation(Aggregation):

    """
    This aggregation collects data for the SDK sum metric point.
    """

    def __init__(self, instrument):
        self._value = None
        self._timestamp = _time_ns()

    def aggregate(self, value):
        self._value = value
        self._timestamp = _time_ns()


class ExplicitBucketHistogramAggregation(Aggregation):

    """
    This aggregation collects data for the SDK sum metric point.
    """

    def __init__(
        self,
        instrument,
        *args,
        boundaries=(0, 5, 10, 25, 50, 75, 100, 250, 500, 1000, inf),
        record_min_max=True,
    ):
        super().__init__()
        self._boundaries = boundaries
        self._value = OrderedDict([(key, 0) for key in boundaries])
        self._min = inf
        self._max = -inf
        self._sum = 0
        self._instrument = instrument
        self._record_min_max = record_min_max

    @property
    def min(self):
        if not self._record_min_max:
            _logger.warning("Min is not being recorded")

        return self._min

    @property
    def max(self):
        if not self._record_min_max:
            _logger.warning("Max is not being recorded")

        return self._max

    @property
    def sum(self):
        if isinstance(self._instrument, _Monotonic):
            return self._sum

        _logger.warning(
            "Sum is not filled out when the associated "
            "instrument is not monotonic"
        )

    def aggregate(self, value):
        if self._record_min_max:
            self._min = min(self._min, value)
            self._max = max(self._max, value)

        if isinstance(self._instrument, _Monotonic):
            self._sum += value

        for key in self._value.keys():

            if value < key:
                self._value[key] = self._value[key] + value

                break
