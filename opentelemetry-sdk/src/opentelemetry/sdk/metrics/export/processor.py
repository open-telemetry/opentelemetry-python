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
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util import get_dict_as_key


class Processor:
    """Base class for all processor types.

    The processor is responsible for storing the aggregators and aggregated
    values received from updates from metrics in the meter. The stored values
    will be sent to an exporter for exporting.
    """

    def __init__(self, stateful: bool, resource: Resource):
        self._batch_map = {}
        # stateful=True indicates the processor computes checkpoints from over
        # the process lifetime. False indicates the processor computes
        # checkpoints which describe the updates of a single collection period
        # (deltas)
        self.stateful = stateful
        self._resource = resource

    def checkpoint_set(self) -> Sequence[MetricRecord]:
        """Returns a list of MetricRecords used for exporting.

        The list of MetricRecords is a snapshot created from the current
        data in all of the aggregators in this processor.
        """
        metric_records = []
        # pylint: disable=W0612
        for (
            (instrument, aggregator_type, _, labels),
            aggregator,
        ) in self._batch_map.items():
            metric_records.append(
                MetricRecord(instrument, labels, aggregator, self._resource)
            )
        return metric_records

    def finished_collection(self):
        """Performs certain post-export logic.

        For processors that are stateless, resets the batch map.
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
        # If two aggregators are the same but with different configs, they are still two valid unique records
        # (for example, two histogram views with different buckets)
        key = (
            record.instrument,
            aggregator.__class__,
            get_dict_as_key(aggregator.config),
            record.labels,
        )

        batch_value = self._batch_map.get(key)

        if batch_value:
            # Update the stored checkpointed value if exists. The call to merge
            # here combines only identical records (same key).
            batch_value.merge(aggregator)
            return

        # create a copy of the aggregator and update
        # it with the current checkpointed value for long-term storage
        aggregator = record.aggregator.__class__(
            config=record.aggregator.config
        )
        aggregator.merge(record.aggregator)

        self._batch_map[key] = aggregator
