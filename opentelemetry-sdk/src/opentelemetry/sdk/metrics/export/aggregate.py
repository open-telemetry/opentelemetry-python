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
from math import inf

from opentelemetry.util import time_ns

logger = logging.getLogger(__name__)


class Aggregator(abc.ABC):
    """Base class for aggregators.

    Aggregators are responsible for holding aggregated values and taking a
    snapshot of these values upon export (checkpoint).
    """

    def __init__(self, config=None):
        self._lock = threading.Lock()
        self.last_update_timestamp = 0
        self.initial_checkpoint_timestamp = 0
        self.checkpointed = True
        if config is not None:
            self.config = config
        else:
            self.config = {}

    @abc.abstractmethod
    def update(self, value):
        """Updates the current with the new value."""
        if self.checkpointed:
            self.initial_checkpoint_timestamp = time_ns()
            self.checkpointed = False
        self.last_update_timestamp = time_ns()

    @abc.abstractmethod
    def take_checkpoint(self):
        """Stores a snapshot of the current value."""
        self.checkpointed = True

    @abc.abstractmethod
    def merge(self, other):
        """Combines two aggregator values."""
        self.last_update_timestamp = max(
            self.last_update_timestamp, other.last_update_timestamp
        )
        self.initial_checkpoint_timestamp = max(
            self.initial_checkpoint_timestamp,
            other.initial_checkpoint_timestamp,
        )

    def _verify_type(self, other):
        if isinstance(other, self.__class__):
            return True
        logger.warning(
            "Error in merging %s with %s.",
            self.__class__.__name__,
            other.__class__.__name__,
        )
        return False


class SumAggregator(Aggregator):
    """Aggregator for counter metrics."""

    def __init__(self, config=None):
        super().__init__(config=config)
        self.current = 0
        self.checkpoint = 0

    def update(self, value):
        with self._lock:
            self.current += value
            super().update(value)

    def take_checkpoint(self):
        with self._lock:
            self.checkpoint = self.current
            self.current = 0
            super().take_checkpoint()

    def merge(self, other):
        if self._verify_type(other):
            with self._lock:
                self.checkpoint += other.checkpoint
                super().merge(other)


class MinMaxSumCountAggregator(Aggregator):
    """Aggregator for ValueRecorder metrics that keeps min, max, sum, count."""

    _TYPE = namedtuple("minmaxsumcount", "min max sum count")
    _EMPTY = _TYPE(inf, -inf, 0, 0)

    def __init__(self, config=None):
        super().__init__(config=config)
        self.current = self._EMPTY
        self.checkpoint = self._EMPTY

    def update(self, value):
        with self._lock:
            self.current = self._TYPE(
                min(self.current.min, value),
                max(self.current.max, value),
                self.current.sum + value,
                self.current.count + 1,
            )
            super().update(value)

    def take_checkpoint(self):
        with self._lock:
            self.checkpoint = self.current
            self.current = self._EMPTY
            super().take_checkpoint()

    def merge(self, other):
        if self._verify_type(other):
            with self._lock:
                self.checkpoint = self._TYPE(
                    min(self.checkpoint.min, other.checkpoint.min),
                    max(self.checkpoint.max, other.checkpoint.max),
                    self.checkpoint.sum + other.checkpoint.sum,
                    self.checkpoint.count + other.checkpoint.count,
                )
                super().merge(other)


class HistogramAggregator(Aggregator):
    """Aggregator for ValueRecorder metrics that keeps a histogram of values."""

    def __init__(self, config=None):
        super().__init__(config=config)
        # no buckets except < 0 and >
        bounds = (0,)
        config_bounds = self.config.get("bounds")
        if config_bounds is not None:
            if all(
                config_bounds[i] < config_bounds[i + 1]
                for i in range(len(config_bounds) - 1)
            ):
                bounds = config_bounds
            else:
                logger.warning(
                    "Bounds must be all different and sorted in increasing"
                    " order. Using default."
                )

        self.current = OrderedDict([(bb, 0) for bb in bounds])
        self.current[inf] = 0
        self.checkpoint = OrderedDict([(bb, 0) for bb in bounds])
        self.checkpoint[inf] = 0

    def update(self, value):
        with self._lock:
            for bb in self.current.keys():
                # find first bucket that value is less than
                if value < bb:
                    self.current[bb] += 1
                    break
            super().update(value)

    def take_checkpoint(self):
        with self._lock:
            self.checkpoint = self.current.copy()
            for bb in self.current.keys():
                self.current[bb] = 0
            super().take_checkpoint()

    def merge(self, other):
        if self._verify_type(other):
            with self._lock:
                if self.checkpoint.keys() == other.checkpoint.keys():
                    for ii, bb in other.checkpoint.items():
                        self.checkpoint[ii] += bb
                    super().merge(other)
                else:
                    logger.warning(
                        "Cannot merge histograms with different buckets."
                    )


class LastValueAggregator(Aggregator):
    """Aggregator that stores last value results."""

    def __init__(self, config=None):
        super().__init__(config=config)
        self.current = None
        self.checkpoint = None

    def update(self, value):
        with self._lock:
            self.current = value
            super().update(value)

    def take_checkpoint(self):
        with self._lock:
            self.checkpoint = self.current
            self.current = None
            super().take_checkpoint()

    def merge(self, other):
        last = self.checkpoint
        super().merge(other)
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

    def update(self, value):
        self.mmsc.update(value)
        self.current = value
        super().update(value)

    def take_checkpoint(self):
        self.mmsc.take_checkpoint()
        self.checkpoint = self._TYPE(*(self.mmsc.checkpoint + (self.current,)))
        super().take_checkpoint()

    def merge(self, other):
        if self._verify_type(other):
            self.mmsc.merge(other.mmsc)
            last = self.checkpoint.last

            self.last_update_timestamp = max(
                self.last_update_timestamp, other.last_update_timestamp
            )

            if self.last_update_timestamp == other.last_update_timestamp:
                last = other.checkpoint.last
            self.checkpoint = self._TYPE(*(self.mmsc.checkpoint + (last,)))
            super().merge(other)
