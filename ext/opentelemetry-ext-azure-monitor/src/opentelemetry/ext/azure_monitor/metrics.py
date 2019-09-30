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

import logging

from opentelemetry.ext.azure_monitor import protocol, transport, util
from opentelemetry.sdk.metrics.export import (
    MetricsExporter,
    MetricsExportResult,
)

logger = logging.getLogger(__name__)


class AzureMonitorMetricsExporter(MetricsExporter, transport.TransportMixin):
    def __init__(self, **options):
        self.options = util.Options(**options)
        util.validate_key(self.options.instrumentation_key)
        self.export_result_type = MetricsExportResult

    def export(self, metric_tuples):
        # Metric tuples is a sequence of metric to label values pairs
        envelopes = tuple(map(self._metric_tuple_to_envelope, metric_tuples))
        return self._transmit(envelopes)

    def _metric_tuple_to_envelope(self, metric_tuple):
        metric = metric_tuple[0]
        label_values = metric_tuple[1]
        handle = metric.get_handle(label_values)
        envelope = protocol.Envelope(
            iKey=self.options.instrumentation_key,
            tags=dict(util.azure_monitor_context),
            time=handle.last_update_timestamp,
        )
        envelope.name = "Microsoft.ApplicationInsights.Metric"
        # label_keys and label_values assumed to have the same length
        properties = {
            metric.label_keys[idx]: label_values[idx]
            for idx, value in enumerate(label_values, start=0)
        }
        data_point = protocol.DataPoint(
            ns=metric.name, name=metric.name, value=handle.data
        )
        data = protocol.MetricData(metrics=[data_point], properties=properties)
        envelope.data = protocol.Data(baseData=data, baseType="MetricData")
        return envelope
