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

import abc
import logging
import threading
from collections import OrderedDict, namedtuple

from opentelemetry.util import time_ns

logger = logging.getLogger(__name__)


class Aggregator(abc.ABC):
    """Base class for aggregators.

    Aggregators are responsible for holding aggregated values and taking a
    snapshot of these values upon export (checkpoint).
    """

    def __init__(self, config=None):
        self.current = None
        self.checkpoint = None
        self.config = config

    @abc.abstractmethod
    def update(self, value):
        """Updates the current with the new value."""

    @abc.abstractmethod
    def take_checkpoint(self):
        """Stores a snapshot of the current value."""

    @abc.abstractmethod
    def merge(self, other):
        """Combines two aggregator values."""


class SumAggregator(Aggregator):
    """Aggregator for counter metrics."""

    def __init__(self, config=None):
        super().__init__(config=config)
        self.current = 0
        self.checkpoint = 0
        self._lock = threading.Lock()
        self.last_update_timestamp = None

    def update(self, value):
        with self._lock:
            self.current += value
            self.last_update_timestamp = time_ns()

    def take_checkpoint(self):
        with self._lock:
            self.checkpoint = self.current
            self.current = 0

    def merge(self, other):
        if verify_type(self, other):
            with self._lock:
                self.checkpoint += other.checkpoint
                self.last_update_timestamp = get_latest_timestamp(
                    self.last_update_timestamp, other.last_update_timestamp
                )


class MinMaxSumCountAggregator(Aggregator):
    """Aggregator for ValueRecorder metrics that keeps min, max, sum, count."""

    _TYPE = namedtuple("minmaxsumcount", "min max sum count")
    _EMPTY = _TYPE(None, None, None, 0)

    @classmethod
    def _merge_checkpoint(cls, val1, val2):
        if val1 is cls._EMPTY:
            return val2
        if val2 is cls._EMPTY:
            return val1
        return cls._TYPE(
            min(val1.min, val2.min),
            max(val1.max, val2.max),
            val1.sum + val2.sum,
            val1.count + val2.count,
        )

    def __init__(self, config=None):
        super().__init__(config=config)
        self.current = self._EMPTY
        self.checkpoint = self._EMPTY
        self._lock = threading.Lock()
        self.last_update_timestamp = None

    def update(self, value):
        with self._lock:
            if self.current is self._EMPTY:
                self.current = self._TYPE(value, value, value, 1)
            else:
                self.current = self._TYPE(
                    min(self.current.min, value),
                    max(self.current.max, value),
                    self.current.sum + value,
                    self.current.count + 1,
                )
            self.last_update_timestamp = time_ns()

    def take_checkpoint(self):
        with self._lock:
            self.checkpoint = self.current
            self.current = self._EMPTY

    def merge(self, other):
        if verify_type(self, other):
            with self._lock:
                self.checkpoint = self._merge_checkpoint(
                    self.checkpoint, other.checkpoint
                )
                self.last_update_timestamp = get_latest_timestamp(
                    self.last_update_timestamp, other.last_update_timestamp
                )


class HistogramAggregator(Aggregator):
    """Agregator for ValueRecorder metrics that keeps a histogram of values."""

    def __init__(self, config=None):
        super().__init__(config=config)
        self._lock = threading.Lock()
        self.last_update_timestamp = None
        boundaries = self.config
        if boundaries and self._validate_boundaries(boundaries):
            self._boundaries = boundaries
        else:
            self._boundaries = (10, 20, 30, 40, 50, 60, 70, 80, 90, 100)
        self.current = OrderedDict([(bb, 0) for bb in self._boundaries])
        self.checkpoint = OrderedDict([(bb, 0) for bb in self._boundaries])
        self.current[">"] = 0
        self.checkpoint[">"] = 0

    # pylint: disable=R0201
    def _validate_boundaries(self, boundaries):
        if not boundaries:
            logger.warning("Bounds is empty. Using default.")
            return False
        if not all(
            boundaries[ii] < boundaries[ii + 1]
            for ii in range(len(boundaries) - 1)
        ):
            logger.warning(
                "Bounds must be sorted in increasing order. Using default."
            )
            return False
        return True

    @classmethod
    def _merge_checkpoint(cls, val1, val2):
        if val1.keys() == val2.keys():
            for ii, bb in val2.items():
                val1[ii] += bb
        else:
            logger.warning("Cannot merge histograms with different buckets.")
        return val1

    def update(self, value):
        with self._lock:
            if self.current is None:
                self.current = [0 for ii in range(len(self._boundaries) + 1)]
            # greater than max value
            if value >= self._boundaries[len(self._boundaries) - 1]:
                self.current[">"] += 1
            else:
                for bb in self._boundaries:
                    # find first bucket that value is less than
                    if value < bb:
                        self.current[bb] += 1
                        break
            self.last_update_timestamp = time_ns()

    def take_checkpoint(self):
        with self._lock:
            self.checkpoint = self.current
            self.current = OrderedDict([(bb, 0) for bb in self._boundaries])
            self.current[">"] = 0

    def merge(self, other):
        if verify_type(self, other):
            with self._lock:
                self.checkpoint = self._merge_checkpoint(
                    self.checkpoint, other.checkpoint
                )
                self.last_update_timestamp = get_latest_timestamp(
                    self.last_update_timestamp, other.last_update_timestamp
                )


class LastValueAggregator(Aggregator):
    """Aggregator that stores last value results."""

    def __init__(self, config=None):
        super().__init__(config=config)
        self._lock = threading.Lock()
        self.last_update_timestamp = None

    def update(self, value):
        with self._lock:
            self.current = value
            self.last_update_timestamp = time_ns()

    def take_checkpoint(self):
        with self._lock:
            self.checkpoint = self.current
            self.current = None

    def merge(self, other):
        last = self.checkpoint
        self.last_update_timestamp = get_latest_timestamp(
            self.last_update_timestamp, other.last_update_timestamp
        )
        if self.last_update_timestamp == other.last_update_timestamp:
            last = other.checkpoint
        self.checkpoint = last


class ValueObserverAggregator(Aggregator):
    """Same as MinMaxSumCount but also with last value."""

    _TYPE = namedtuple("minmaxsumcountlast", "min max sum count last")

    def __init__(self, config=None):
        super().__init__(config=config)
        self.mmsc = MinMaxSumCountAggregator()
        self.current = None
        self.checkpoint = self._TYPE(None, None, None, 0, None)
        self.last_update_timestamp = None

    def update(self, value):
        self.mmsc.update(value)
        self.current = value
        self.last_update_timestamp = time_ns()

    def take_checkpoint(self):
        self.mmsc.take_checkpoint()
        self.checkpoint = self._TYPE(*(self.mmsc.checkpoint + (self.current,)))

    def merge(self, other):
        if verify_type(self, other):
            self.mmsc.merge(other.mmsc)
            last = self.checkpoint.last
            self.last_update_timestamp = get_latest_timestamp(
                self.last_update_timestamp, other.last_update_timestamp
            )
            if self.last_update_timestamp == other.last_update_timestamp:
                last = other.checkpoint.last
            self.checkpoint = self._TYPE(*(self.mmsc.checkpoint + (last,)))


def get_latest_timestamp(time_stamp, other_timestamp):
    if time_stamp is None:
        return other_timestamp
    if other_timestamp is not None:
        if time_stamp < other_timestamp:
            return other_timestamp
    return time_stamp


# pylint: disable=R1705
def verify_type(this, other):
    if isinstance(other, this.__class__):
        return True
    else:
        logger.warning(
            "Error in merging %s with %s.",
            this.__class__.__name__,
            other.__class__.__name__,
        )
        return False
