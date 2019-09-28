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

import json
import logging

import requests

from opentelemetry.ext.azure_monitor import protocol, util
from opentelemetry.sdk.metrics.export import (
    MetricsExporter,
    MetricsExportResult,
)


logger = logging.getLogger(__name__)


class AzureMonitorMetricsExporter(MetricsExporter):
    def __init__(self, **options):
        self.options = util.Options(**options)
        if not self.options.instrumentation_key:
            raise ValueError("The instrumentation_key is not provided.")

    def export(self, metric_tuples):
        # Metric tuples is a sequence of metric to label values pairs
        envelopes = tuple(map(self.metric_tuple_to_envelope, metric_tuples))

        try:
            response = requests.post(
                url=self.options.endpoint,
                data=json.dumps(envelopes),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json; charset=utf-8",
                },
                timeout=self.options.timeout,
            )
        except requests.RequestException as ex:
            logger.warning("Transient client side error %s.", ex)
            return MetricsExportResult.FAILED_RETRYABLE

        text = "N/A"
        data = None  # noqa pylint: disable=unused-variable
        try:
            text = response.text
        except Exception as ex:  # noqa pylint: disable=broad-except
            logger.warning("Error while reading response body %s.", ex)
        else:
            try:
                data = json.loads(text)  # noqa pylint: disable=unused-variable
            except Exception:  # noqa pylint: disable=broad-except
                pass

        if response.status_code == 200:
            logger.info("Transmission succeeded: %s.", text)
            return MetricsExportResult.SUCCESS

        if response.status_code in (
            206,  # Partial Content
            429,  # Too Many Requests
            500,  # Internal Server Error
            503,  # Service Unavailable
        ):
            return MetricsExportResult.FAILED_RETRYABLE

        return MetricsExportResult.FAILED_NOT_RETRYABLE

    def metric_tuple_to_envelope(self, metric_tuple):
        metric = metric_tuple[0]
        label_values = metric_tuple[1]
        handle = metric.get_handle(label_values)
        envelope = protocol.Envelope(
            iKey=self.options.instrumentation_key,
            tags=dict(util.azure_monitor_context),
            time=handle.time_stamp.isoformat(),
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
