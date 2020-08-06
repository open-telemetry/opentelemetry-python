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

"""
    Exemplars are sample data points for aggregators. For more information, see the `spec <https://github.com/open-telemetry/oteps/pull/113>`_

    Every synchronous aggregator is instrumented with two exemplar recorders:
        1. A "trace" exemplar sampler, which only samples exemplars if they have a sampled trace context (and can pick exemplars with other biases, ie min + max).
        2. A "statistical" exemplar sampler, which samples exemplars without bias (ie no preferenced for traced exemplars)

    To use an exemplar recorder, pass in two arguments to the aggregator config in views (see the :ref:`Exemplars` example for an example):
        "num_exemplars": The number of exemplars to record (if applicable, in each bucket). Note that in non-statistical mode the recorder may not use "num_exemplars"
        "statistical_exemplars": If exemplars should be recorded statistically

    For exemplars to be recorded, `num_exemplars` must be greater than 0.
"""

import abc
import itertools
import random
from typing import List, Optional, Tuple, Union

from opentelemetry.context import get_current
from opentelemetry.util import time_ns


class Exemplar:
    """
        A sample data point for an aggregator. Exemplars represent individual measurements recorded.
    """

    def __init__(
        self,
        value: Union[int, float],
        timestamp: int,
        dropped_labels: Optional[Tuple[Tuple[str, str]]] = None,
        span_id: Optional[bytes] = None,
        trace_id: Optional[bytes] = None,
        sample_count: Optional[float] = None,
    ):
        self._value = value
        self._timestamp = timestamp
        self._span_id = span_id
        self._trace_id = trace_id
        self._sample_count = sample_count
        self._dropped_labels = dropped_labels

    def __repr__(self):
        return "Exemplar(value={}, timestamp={}, labels={}, context={{'span_id':{}, 'trace_id':{}}})".format(
            self._value,
            self._timestamp,
            dict(self._dropped_labels) if self._dropped_labels else None,
            self._span_id,
            self._trace_id,
        )

    @property
    def value(self):
        """The current value of the Exemplar point"""
        return self._value

    @property
    def timestamp(self):
        """The time that this Exemplar's value was recorded"""
        return self._timestamp

    @property
    def span_id(self):
        """The span ID of the context when the exemplar was recorded"""
        return self._span_id

    @property
    def trace_id(self):
        """The trace ID of the context when the exemplar was recorded"""
        return self._trace_id

    @property
    def dropped_labels(self):
        """Labels that were dropped by the aggregator but still passed by the user"""
        return self._dropped_labels

    @property
    def sample_count(self):
        """For statistical exemplars, how many measurements a single exemplar represents"""
        return self._sample_count

    def set_sample_count(self, count: float):
        self._sample_count = count


class ExemplarSampler(abc.ABC):
    """
        Abstract class to sample `k` exemplars in some way through a stream of incoming measurements
    """

    def __init__(self, k: int, statistical: bool = False):
        self._k = k
        self._statistical = statistical
        self._sample_set = []

    @abc.abstractmethod
    def sample(self, exemplar: Exemplar, **kwargs):
        """
        Given an exemplar, determine if it should be sampled or not
        """

    @property
    @abc.abstractmethod
    def sample_set(self):
        """
        Return the list of exemplars that have been sampled
        """

    @abc.abstractmethod
    def merge(self, set1: List[Exemplar], set2: List[Exemplar]):
        """
        Given two lists of sampled exemplars, merge them while maintaining the invariants specified by this sampler
        """

    @abc.abstractmethod
    def reset(self):
        """
        Reset the sampler
        """


class RandomExemplarSampler(ExemplarSampler):
    """
        Randomly sample a set of k exemplars from a stream. Each measurement in the stream
        will have an equal chance of being sampled.

        If `RandomExemplarSampler` is specified to be statistical, it will add a sample_count to every exemplar it records.
        This value will be equal to the number of measurements recorded per every exemplar measured - all exemplars will have the same sample_count value.
    """

    def __init__(self, k: int, statistical: bool = False):
        super().__init__(k, statistical=statistical)
        self.rand_count = 0

    def sample(self, exemplar: Exemplar, **kwargs):
        self.rand_count += 1

        if len(self._sample_set) < self._k:
            self._sample_set.append(exemplar)
            return

        # We sample a random subset of a stream using "Algorithm R":
        # https://en.wikipedia.org/wiki/Reservoir_sampling#Simple_algorithm
        replace_index = random.randint(0, self.rand_count - 1)

        if replace_index < self._k:
            self._sample_set[replace_index] = exemplar

    def merge(self, set1: List[Exemplar], set2: List[Exemplar]):
        """
        Assume that set2 is the latest set of exemplars.
        For simplicity, we will just keep set2 and assume set1 has already been exported.
        This may need to change with a different SDK implementation.
        """
        return set2

    @property
    def sample_set(self):
        if self._statistical:
            for exemplar in self._sample_set:
                exemplar.set_sample_count(
                    self.rand_count / len(self._sample_set)
                )
        return self._sample_set

    def reset(self):
        self._sample_set = []
        self.rand_count = 0


class MinMaxExemplarSampler(ExemplarSampler):
    """
        Sample the minimum and maximum measurements recorded only
    """

    def __init__(self, k: int, statistical: bool = False):
        # K will always be 2 (min and max), and selecting min and max can never be statistical
        super().__init__(2, statistical=False)
        self._sample_set = []

    def sample(self, exemplar: Exemplar, **kwargs):
        self._sample_set = [
            min(
                self._sample_set + [exemplar],
                key=lambda exemplar: exemplar.value,
            ),
            max(
                self._sample_set + [exemplar],
                key=lambda exemplar: exemplar.value,
            ),
        ]
        if self._sample_set[0] == self._sample_set[1]:
            self._sample_set = [self._sample_set[0]]

    @property
    def sample_set(self):
        return self._sample_set

    def merge(self, set1: List[Exemplar], set2: List[Exemplar]):
        """
        Assume that set2 is the latest set of exemplars.
        For simplicity, we will just keep set2 and assume set1 has already been exported.
        This may need to change with a different SDK implementation.
        """
        return set2

    def reset(self):
        self._sample_set = []


class BucketedExemplarSampler(ExemplarSampler):
    """
        Randomly sample k exemplars for each bucket in the aggregator.

        If `BucketedExemplarSampler` is specified to be statistical, it will add a sample_count to every exemplar it records.
        This value will be equal to `len(bucket.exemplars) / bucket.count`, that is the number of measurements each exemplar represents.
    """

    def __init__(
        self, k: int, statistical: bool = False, boundaries: list = None
    ):
        super().__init__(k)
        self._boundaries = boundaries
        self._sample_set = [
            RandomExemplarSampler(k, statistical=statistical)
            for _ in range(len(self._boundaries) + 1)
        ]

    def sample(self, exemplar: Exemplar, **kwargs):
        bucket_index = kwargs.get("bucket_index")
        if bucket_index is None:
            return

        self._sample_set[bucket_index].sample(exemplar)

    @property
    def sample_set(self):
        return list(
            itertools.chain.from_iterable(
                [sampler.sample_set for sampler in self._sample_set]
            )
        )

    def merge(self, set1: List[Exemplar], set2: List[Exemplar]):
        """
        Assume that set2 is the latest set of exemplars.
        For simplicity, we will just keep set2 and assume set1 has already been exported.
        This may need to change with a different SDK implementation.
        """
        return set2

    def reset(self):
        for sampler in self._sample_set:
            sampler.reset()


class ExemplarManager:
    """
        Manages two different exemplar samplers:
        1. A "trace" exemplar sampler, which only samples exemplars if they have a sampled trace context.
        2. A "statistical" exemplar sampler, which samples exemplars without bias (ie no preferenced for traced exemplars)
    """

    def __init__(
        self,
        config: dict,
        default_exemplar_sampler: ExemplarSampler,
        statistical_exemplar_sampler: ExemplarSampler,
        **kwargs
    ):
        if config:
            self.exemplars_count = config.get("num_exemplars", 0)
            self.record_exemplars = self.exemplars_count > 0
            self.statistical_exemplars = config.get(
                "statistical_exemplars", False
            )
            if self.statistical_exemplars:
                self.exemplar_sampler = statistical_exemplar_sampler(
                    self.exemplars_count,
                    statistical=self.statistical_exemplars,
                    **kwargs
                )
            else:
                self.exemplar_sampler = default_exemplar_sampler(
                    self.exemplars_count,
                    statistical=self.statistical_exemplars,
                    **kwargs
                )
        else:
            self.record_exemplars = False

    def sample(
        self,
        value: Union[int, float],
        dropped_labels: Tuple[Tuple[str, str]],
        **kwargs
    ):
        context = get_current()

        is_sampled = (
            "current-span" in context
            and context["current-span"].get_context().trace_flags.sampled
            if context
            else False
        )

        # if not statistical, we want to gather traced exemplars only - so otherwise don't sample
        if self.record_exemplars and (
            is_sampled or self.statistical_exemplars
        ):
            span_id = (
                context["current-span"].context.span_id if context else None
            )
            trace_id = (
                context["current-span"].context.trace_id if context else None
            )
            self.exemplar_sampler.sample(
                Exemplar(value, time_ns(), dropped_labels, span_id, trace_id),
                **kwargs
            )

    def take_checkpoint(self):
        if self.record_exemplars:
            ret = self.exemplar_sampler.sample_set
            self.exemplar_sampler.reset()
            return ret
        return []

    def merge(
        self,
        checkpoint_exemplars: List[Exemplar],
        other_checkpoint_exemplars: List[Exemplar],
    ):
        if self.record_exemplars:
            return self.exemplar_sampler.merge(
                checkpoint_exemplars, other_checkpoint_exemplars
            )
        return []
