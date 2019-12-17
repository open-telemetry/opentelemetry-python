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

from typing import Type
from opentelemetry.metrics import Counter, MetricT
from opentelemetry.sdk.metrics.export import MetricRecord
from opentelemetry.sdk.metrics.export.aggregate import CounterAggregator


class Batcher(abc.ABC):

    def __init__(self, keep_state):
        self.batch_map = {}
        self.keep_state = keep_state

    def aggregator_for(self, metric_type: Type[MetricT]):
        if metric_type == Counter:
            return CounterAggregator()
        else:
            # TODO: Add other aggregators
            return CounterAggregator()

    def check_point_set(self):
        metric_records = []
        for key, value in self.batch_map.items():
            metric_records.append(MetricRecord(value[0], value[1], key[0]))
        return metric_records

    def finished_collection(self):
        if not self.keep_state:
            self.batch_map = {}

    @abc.abstractmethod
    def process(self, record):
        pass


class UngroupedBatcher(Batcher):

    def process(self, record):
        # checkpoints the current aggregator value to be collected for export
        record.aggregator.checkpoint()
        # TODO: Race case of incoming update at the same time as process
        batch_key = (record.metric, record.label_set.encoded)
        batch_value = self.batch_map.get(batch_key)
        if not batch_value:
            self.batch_map[batch_key] = (record.aggregator, record.label_set)
