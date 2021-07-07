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
from math import inf
from types import SimpleNamespace

_logger = getLogger(__name__)


class Aggregator(ABC):
    """Aggregator.

    sdfsd
    """

    @classmethod
    @abstractmethod
    def _get_value_name(cls):
        """_get_value_name."""
        pass

    @abstractmethod
    def _get_initial_value(self):
        pass

    def aggregate(self, value):
        if self.__class__.__bases__[0] is Aggregator:
            self._value = self._aggregate(value)

        else:
            for parent_class in self.__class__.__bases__:
                getattr(self, parent_class._get_value_name()).aggregate(value)

    @abstractmethod
    def _aggregate(self, new_value):
        """_aggregate.

        :param new_value:
        """
        pass

    def _add_attributes(self, *args, **kwargs):
        self._value = self._get_initial_value()

    def _initialize(
        self,
        type_,
        self_args,
        self_kwargs,
        parent_args,
        parent_kwargs
    ):

        if self.__class__ == type_:
            self._add_attributes(*self_args, **self_kwargs)
            setattr(
                self.__class__, "value", property(lambda self: self._value)
            )

        else:
            setattr(
                self,
                type_._get_value_name(),
                type_(*self_args, **self_kwargs)
            )
            super(type_, self).__init__(*parent_args, **parent_kwargs)


class MinAggregator(Aggregator):
    def __init__(self, *parent_args, **parent_kwargs):
        self._initialize(MinAggregator, [], {}, parent_args, parent_kwargs)

    @classmethod
    def _get_value_name(cls):
        return "min"

    def _get_initial_value(self):
        return inf

    def _aggregate(self, value: int) -> int:
        """_aggregate.

        :param value:
        :type value: int
        :rtype: int
        """

        return min(self._value, value)


class MaxAggregator(Aggregator):
    def __init__(self, *parent_args, **parent_kwargs):
        self._initialize(MaxAggregator, [], {}, parent_args, parent_kwargs)

    @classmethod
    def _get_value_name(cls):
        return "max"

    def _get_initial_value(self):
        return -inf

    def _aggregate(self, value):

        return max(self._value, value)


class SumAggregator(Aggregator):
    def __init__(self, *parent_args, **parent_kwargs):
        self._initialize(SumAggregator, [], {}, parent_args, parent_kwargs)

    @classmethod
    def _get_value_name(cls):
        return "sum"

    def _get_initial_value(self):
        return 0

    def _aggregate(self, value):

        return sum([self._value, value])


class CountAggregator(Aggregator):
    def __init__(self, *parent_args, **parent_kwargs):
        self._initialize(CountAggregator, [], {}, parent_args, parent_kwargs)

    @classmethod
    def _get_value_name(cls):
        return "count"

    def _get_initial_value(self):
        return 0

    def _aggregate(self, value):

        return self._value + 1


class LastAggregator(Aggregator):
    def __init__(self, *parent_args, **parent_kwargs):
        self._initialize(LastAggregator, [], {}, parent_args, parent_kwargs)

    @classmethod
    def _get_value_name(cls):
        return "last"

    def _get_initial_value(self):
        return None

    def _aggregate(self, value):

        return value


class HistogramAggregator(Aggregator):

    def __init__(self, buckets, *parent_args, **parent_kwargs):
        self._initialize(
            HistogramAggregator, [buckets], {}, parent_args, parent_kwargs
        )

    def _add_attributes(self, buckets):
        self._buckets = buckets
        return super()._add_attributes()

    @classmethod
    def _get_value_name(cls):
        return "histogram"

    def _get_initial_value(self):

        return [
            SimpleNamespace(
                lower=SimpleNamespace(inclusive=True, value=lower),
                upper=SimpleNamespace(inclusive=False, value=upper),
                count=0,
            )
            if index < len(self._buckets) - 2
            else SimpleNamespace(
                lower=SimpleNamespace(inclusive=True, value=lower),
                upper=SimpleNamespace(inclusive=True, value=upper),
                count=0,
            )
            for index, (lower, upper) in enumerate(
                zip(self._buckets, self._buckets[1:])
            )
        ]

    def _aggregate(self, value):

        for bucket in self._value:
            if value < bucket.lower.value:
                _logger.warning("Value %s below lower histogram bound" % value)
                break

            if (bucket.upper.inclusive and value <= bucket.upper.value) or (
                value < bucket.upper.value
            ):
                bucket.count = bucket.count + 1
                break

        else:

            _logger.warning("Value %s over upper histogram bound" % value)

        return self._value


class BoundSetAggregator(Aggregator):

    def __init__(
        self, lower_bound, upper_bound, *parent_args, **parent_kwargs
    ):
        self._initialize(
            BoundSetAggregator,
            [lower_bound, upper_bound],
            {},
            parent_args,
            parent_kwargs
        )

    def _add_attributes(self, lower_bound, upper_bound):
        self._lower_bound = lower_bound
        self._upper_bound = upper_bound
        return super()._add_attributes()

    @classmethod
    def _get_value_name(cls):
        return "boundset"

    def _get_initial_value(self):

        return set()

    def _aggregate(self, value):

        if value < self._lower_bound:
            _logger.warning("Value %s below lower set bound" % value)

        elif value > self._upper_bound:
            _logger.warning("Value %s over upper set bound" % value)

        else:
            self._value.add(value)

        return self._value


class MinMaxSumAggregator(MinAggregator, MaxAggregator, SumAggregator):
    @classmethod
    def _get_value_name(cls):
        return "minmaxsum"


class MinMaxSumHistogramAggregator(
    MinAggregator, MaxAggregator, SumAggregator, HistogramAggregator
):
    @classmethod
    def _get_value_name(cls):
        return "minmaxsum"
