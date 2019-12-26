# Copyright 2019, OpenTelemetry Authors
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

from typing import Sequence, Type
from opentelemetry.metrics import Counter, MetricT
from opentelemetry.sdk.metrics.export import MetricRecord
from opentelemetry.sdk.metrics.export.aggregate import (
    Aggregator,
    CounterAggregator,
)


class Batcher(abc.ABC):
    """Base class for all batcher types.

    The batcher is responsible for storing the aggregators and aggregated
    received from updates from metrics in the meter. The stored values will be
    sent to an exporter for exporting.
    """

    def __init__(self, keep_state: bool):
        self.batch_map = {}
        # keep_state=True indicates the batcher computes checkpoints from over
        # the process lifetime. False indicates the batcher computes
        # checkpoints which descrive the updates of a single collection period
        # (deltas)
        self.keep_state = keep_state

    def aggregator_for(self, metric_type: Type[MetricT]) -> Aggregator:
        """Returns an aggregator based off metric type.

        Aggregators keep track of and updates values when metrics get updated.
        """
        if metric_type == Counter:
            return CounterAggregator()
        else:
            # TODO: Add other aggregators
            return CounterAggregator()

    def check_point_set(self) -> Sequence[MetricRecord]:
        """Returns a list of MetricRecords used for exporting.

        The list of MetricRecords is a snapshot created from the current
        data in all of the aggregators in this batcher.
        """
        metric_records = []
        for key, value in self.batch_map.items():
            metric_records.append(MetricRecord(value[0], value[1], key[0]))
        return metric_records

    def finished_collection(self):
        """Performs certain post-export logic.

        For batchers that are stateless, resets the batch map.
        """
        if not self.keep_state:
            self.batch_map = {}

    @abc.abstractmethod
    def process(self, record: "Record") -> None:
        """Stores record information to be ready for exporting.

        Depending on type of batcher, performs pre-export logic, such as
        filtering records based off of keys.
        """


class UngroupedBatcher(Batcher):
    """Accepts all records and passes them for exporting"""

    def process(self, record: "Record"):
        # Checkpoints the current aggregator value to be collected for export
        record.aggregator.checkpoint()
        batch_key = (record.metric, record.label_set.encoded)
        batch_value = self.batch_map.get(batch_key)
        aggregator = record.aggregator
        if batch_value:
            # Update the stored checkpointed value if exists. This is for cases
            # when an update comes at the same time as a checkpoint call
            batch_value[0].merge(aggregator)
            return
        if self.keep_state:
            # if stateful batcher, create a copy of the aggregator and update
            # it with the current checkpointed value for long-term storage
            aggregator = self.aggregator_for(record.metric.__class__)
            aggregator.merge(record.aggregator)
        self.batch_map[batch_key] = (aggregator, record.label_set)
