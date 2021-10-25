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
from math import inf

from opentelemetry.proto.metrics.v1.metrics_pb2 import (
    AGGREGATION_TEMPORALITY_CUMULATIVE,
    AGGREGATION_TEMPORALITY_DELTA,
)
from opentelemetry.util._time import _time_ns


class Aggregation(ABC):
    def __init__(self):
        self._value = 0

    @property
    def value(self):
        return self._value

    @abstractmethod
    def aggregate(self, value):
        pass

    @abstractmethod
    def collect(self):
        pass


class NoneAggregation(Aggregation):
    """
    This aggregation drops all instrument measurements.
    """

    def aggregate(self, value):
        pass

    def collect(self):
        return self._value


class SumAggregation(Aggregation):
    """
    This aggregation collects data for the SDK sum metric point.
    """

    def __init__(self, temporality=AGGREGATION_TEMPORALITY_CUMULATIVE):
        super().__init__()
        self._temporality = temporality

    def aggregate(self, value):
        self._value = self._value + value

    def collect(self):
        value = self._value
        if self._temporality == AGGREGATION_TEMPORALITY_DELTA:
            self._value = 0

        return value


class LastValueAggregation(Aggregation):

    """
    This aggregation collects data for the SDK sum metric point.
    """

    def __init__(self):
        super().__init__()
        self._timestamp = _time_ns()

    def aggregate(self, value):
        self._value = value
        self._timestamp = _time_ns()

    def collect(self):
        return self._value


class ExplicitBucketHistogramAggregation(Aggregation):

    """
    This aggregation collects data for the SDK sum metric point.
    """

    def __init__(
        self,
        temporality=AGGREGATION_TEMPORALITY_CUMULATIVE,
        boundaries=(0, 5, 10, 25, 50, 75, 100, 250, 500, 1000, inf),
    ):
        super().__init__()
        self._temporality = temporality
        self._boundaries = boundaries
        self._value = OrderedDict([(key, 0) for key in boundaries])

    def aggregate(self, value):
        for key in self._value.keys():

            if value < key:
                self._value[key] = self._value[key] + value

                break

    def collect(self):
        value = self._value
        if self._temporality == AGGREGATION_TEMPORALITY_DELTA:
            self._value = OrderedDict([(key, 0) for key in self._boundaries])

        return value
