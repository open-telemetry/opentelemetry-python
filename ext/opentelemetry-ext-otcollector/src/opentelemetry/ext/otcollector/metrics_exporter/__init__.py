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

"""OpenTelemetry Collector Metrics Exporter."""

import logging
from typing import Sequence

import grpc
from opencensus.proto.agent.metrics.v1 import (
    metrics_service_pb2,
    metrics_service_pb2_grpc,
)
from opencensus.proto.metrics.v1 import metrics_pb2

import opentelemetry.ext.otcollector.util as utils
from opentelemetry.sdk.metrics import Counter, Metric
from opentelemetry.sdk.metrics.export import (
    MetricRecord,
    MetricsExporter,
    MetricsExportResult,
    aggregate,
)

DEFAULT_ENDPOINT = "localhost:55678"

logger = logging.getLogger(__name__)


# pylint: disable=no-member
class CollectorMetricsExporter(MetricsExporter):
    """OpenTelemetry Collector metrics exporter.

    Args:
        endpoint: OpenTelemetry Collector OpenCensus receiver endpoint.
        service_name: Name of Collector service.
        host_name: Host name.
        client: MetricsService client stub.
    """

    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        service_name: str = None,
        host_name: str = None,
        client: metrics_service_pb2_grpc.MetricsServiceStub = None,
    ):
        self.endpoint = endpoint
        if client is None:
            channel = grpc.insecure_channel(self.endpoint)
            self.client = metrics_service_pb2_grpc.MetricsServiceStub(
                channel=channel
            )
        else:
            self.client = client

        self.node = utils.get_node(service_name, host_name)

    def export(
        self, metric_records: Sequence[MetricRecord]
    ) -> MetricsExportResult:
        try:
            responses = self.client.Export(
                self.generate_metrics_requests(metric_records)
            )

            # Read response
            for _ in responses:
                pass

        except grpc.RpcError:
            return MetricsExportResult.FAILURE

        return MetricsExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    def generate_metrics_requests(
        self, metrics: Sequence[MetricRecord]
    ) -> metrics_service_pb2.ExportMetricsServiceRequest:
        collector_metrics = translate_to_collector(metrics)
        service_request = metrics_service_pb2.ExportMetricsServiceRequest(
            node=self.node, metrics=collector_metrics
        )
        yield service_request


# pylint: disable=too-many-branches
def translate_to_collector(
    metric_records: Sequence[MetricRecord],
) -> Sequence[metrics_pb2.Metric]:
    collector_metrics = []
    for metric_record in metric_records:

        label_values = []
        label_keys = []
        for label_tuple in metric_record.labels:
            label_keys.append(metrics_pb2.LabelKey(key=label_tuple[0]))
            label_values.append(
                metrics_pb2.LabelValue(
                    has_value=label_tuple[1] is not None, value=label_tuple[1]
                )
            )

        metric_descriptor = metrics_pb2.MetricDescriptor(
            name=metric_record.metric.name,
            description=metric_record.metric.description,
            unit=metric_record.metric.unit,
            type=get_collector_metric_type(metric_record.metric),
            label_keys=label_keys,
        )

        timeseries = metrics_pb2.TimeSeries(
            label_values=label_values,
            points=[get_collector_point(metric_record)],
        )
        collector_metrics.append(
            metrics_pb2.Metric(
                metric_descriptor=metric_descriptor, timeseries=[timeseries]
            )
        )
    return collector_metrics


# pylint: disable=no-else-return
def get_collector_metric_type(metric: Metric) -> metrics_pb2.MetricDescriptor:
    if isinstance(metric, Counter):
        if metric.value_type == int:
            return metrics_pb2.MetricDescriptor.CUMULATIVE_INT64
        elif metric.value_type == float:
            return metrics_pb2.MetricDescriptor.CUMULATIVE_DOUBLE
    return metrics_pb2.MetricDescriptor.UNSPECIFIED


def get_collector_point(metric_record: MetricRecord) -> metrics_pb2.Point:
    # TODO: horrible hack to get original list of keys to then get the bound
    # instrument
    point = metrics_pb2.Point(
        timestamp=utils.proto_timestamp_from_time_ns(
            metric_record.aggregator.last_update_timestamp
        )
    )
    if metric_record.metric.value_type == int:
        point.int64_value = metric_record.aggregator.checkpoint
    elif metric_record.metric.value_type == float:
        point.double_value = metric_record.aggregator.checkpoint
    else:
        raise TypeError(
            "Unsupported metric type: {}".format(
                metric_record.metric.value_type
            )
        )
    return point
