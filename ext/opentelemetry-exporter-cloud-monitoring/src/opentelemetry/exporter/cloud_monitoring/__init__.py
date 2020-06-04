import logging
from typing import Optional, Sequence

import google.auth
from google.api.label_pb2 import LabelDescriptor
from google.api.metric_pb2 import MetricDescriptor
from google.cloud.monitoring_v3 import MetricServiceClient
from google.cloud.monitoring_v3.proto.metric_pb2 import TimeSeries

from opentelemetry.sdk.metrics.export import (
    MetricRecord,
    MetricsExporter,
    MetricsExportResult,
)
from opentelemetry.sdk.metrics.export.aggregate import CounterAggregator

logger = logging.getLogger(__name__)
MAX_BATCH_WRITE = 200


# pylint is unable to resolve members of protobuf objects
# pylint: disable=no-member
class CloudMonitoringMetricsExporter(MetricsExporter):
    """ Implementation of Metrics Exporter to Google Cloud Monitoring"""

    def __init__(self, project_id=None, client=None):
        self.client = client or MetricServiceClient()
        if not project_id:
            _, self.project_id = google.auth.default()
        else:
            self.project_id = project_id
        self.project_name = self.client.project_path(self.project_id)
        self._metric_descriptors = {}

    def _add_resource_info(self, series: TimeSeries) -> None:
        """ Add Google resource specific information (e.g. instance id, region)

        :param series: ProtoBuf TimeSeries
        :return:
        """
        # TODO: Leverage this better

    def _batch_write(self, series: TimeSeries) -> None:
        """ Cloud Monitoring allows writing up to 200 time series at once

        :param series: ProtoBuf TimeSeries
        :return:
        """
        write_ind = 0
        while write_ind < len(series):
            self.client.create_time_series(
                self.project_name,
                series[write_ind : write_ind + MAX_BATCH_WRITE],
            )
            write_ind += MAX_BATCH_WRITE

    def _get_metric_descriptor(
        self, record: MetricRecord
    ) -> Optional[MetricDescriptor]:
        """ We can map Metric to MetricDescriptor using Metric.name or
        MetricDescriptor.type. We create the MetricDescriptor if it doesn't
        exist already and cache it. Note that recreating MetricDescriptors is
        a no-op if it already exists.

        :param record:
        :return:
        """
        descriptor_type = "custom.googleapis.com/OpenTelemetry/{}".format(
            record.metric.name
        )
        if descriptor_type in self._metric_descriptors:
            return self._metric_descriptors[descriptor_type]
        descriptor = {
            "name": "display_name",
            "type": descriptor_type,
            "display_name": record.metric.name,
            "description": record.metric.description,
            "labels": [],
        }
        for key, value in record.labels:
            if isinstance(value, str):
                descriptor["labels"].append(
                    LabelDescriptor(key=key, value_type="STRING")
                )
            elif isinstance(value, int):
                descriptor["labels"].append(
                    LabelDescriptor(key=key, value_type="INT64")
                )
            elif isinstance(value, bool):
                descriptor["labels"].append(
                    LabelDescriptor(key=key, value_type="BOOL")
                )
            else:
                logger.warning(
                    "Label value %s is not a string, bool or integer", value
                )
        if isinstance(record.aggregator, CounterAggregator):
            descriptor["metric_kind"] = MetricDescriptor.MetricKind.GAUGE
        else:
            logger.warning(
                "Unsupported aggregation type %s, ignoring it",
                type(record.aggregator).__name__,
            )
            return None
        if record.metric.value_type == int:
            descriptor["value_type"] = MetricDescriptor.ValueType.INT64
        elif record.metric.value_type == float:
            descriptor["value_type"] = MetricDescriptor.ValueType.DOUBLE
        descriptor = self.client.create_metric_descriptor(
            self.project_name, MetricDescriptor(**descriptor)
        )
        self._metric_descriptors[descriptor_type] = descriptor
        return descriptor

    def export(
        self, metric_records: Sequence[MetricRecord]
    ) -> "MetricsExportResult":
        all_series = []
        for record in metric_records:
            metric_descriptor = self._get_metric_descriptor(record)
            if not metric_descriptor:
                continue

            series = TimeSeries()
            self._add_resource_info(series)
            series.metric.type = metric_descriptor.type
            for key, value in record.labels:
                series.metric.labels[key] = value

            point = series.points.add()
            if record.metric.value_type == int:
                point.value.int64_value = record.aggregator.checkpoint
            elif record.metric.value_type == float:
                point.value.double_value = record.aggregator.checkpoint
            seconds, nanos = divmod(
                record.aggregator.last_update_timestamp, 1e9
            )
            point.interval.end_time.seconds = int(seconds)
            point.interval.end_time.nanos = int(nanos)
            all_series.append(series)
        self._batch_write(all_series)
        return MetricsExportResult.SUCCESS
