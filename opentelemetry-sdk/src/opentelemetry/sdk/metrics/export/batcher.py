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

from typing import Sequence

from opentelemetry.sdk.metrics.export import MetricRecord


class Batcher:
    """Base class for all batcher types.

    The batcher is responsible for storing the aggregators and aggregated
    values received from updates from metrics in the meter. The stored values
    will be sent to an exporter for exporting.
    """

    def __init__(self, stateful: bool):
        self._batch_map = {}
        # stateful=True indicates the batcher computes checkpoints from over
        # the process lifetime. False indicates the batcher computes
        # checkpoints which describe the updates of a single collection period
        # (deltas)
        self.stateful = stateful

    def checkpoint_set(self) -> Sequence[MetricRecord]:
        """Returns a list of MetricRecords used for exporting.

        The list of MetricRecords is a snapshot created from the current
        data in all of the aggregators in this batcher.
        """
        metric_records = []
        for (metric, aggregator_type, labels), aggregator in self._batch_map.items():
            metric_records.append(MetricRecord(aggregator, labels, metric))
        return metric_records

    def finished_collection(self):
        """Performs certain post-export logic.

        For batchers that are stateless, resets the batch map.
        """
        if not self.stateful:
            self._batch_map = {}

    def process(self, record) -> None:
        """Stores record information to be ready for exporting."""
        # Checkpoints the current aggregator value to be collected for export
        aggregator = record.aggregator
        aggregator.take_checkpoint()

        # The uniqueness of a batch record is defined by a specific metric
        # using an aggregator type with a specific set of labels.
        key = (record.metric, aggregator.__class__, record.labels)
        batch_value = self._batch_map.get(key)
        if batch_value:
            # Update the stored checkpointed value if exists. The call to merge
            # here combines only identical records (same key).
            batch_value.merge(aggregator)
            return
        if self.stateful:
            # if stateful batcher, create a copy of the aggregator and update
            # it with the current checkpointed value for long-term storage
            aggregator = record.aggregator.__class__(config=record.aggregator.config)
            aggregator.merge(record.aggregator)
        self._batch_map[key] = aggregator
