import logging
import uuid
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
from opentelemetry.sdk.metrics.export.aggregate import SumAggregator

logger = logging.getLogger(__name__)
MAX_BATCH_WRITE = 200
WRITE_INTERVAL = 10


# pylint is unable to resolve members of protobuf objects
# pylint: disable=no-member
class CloudMonitoringMetricsExporter(MetricsExporter):
    """ Implementation of Metrics Exporter to Google Cloud Monitoring"""

    def __init__(
        self, project_id=None, client=None, add_unique_identifier=False
    ):
        """ You can manually pass in project_id and client, or else the
        Exporter will take that informations from Application Default
        Credentials.

        :param project_id: project id of your Google Cloud project
        :param client: Client to upload metrics to Google Cloud Monitoring
        :param add_unique_identifier: Add an identifier to each exporter metric.
        This must be used when there exist two (or more) exporters that may
        export to the same metric name within WRITE_INTERVAL seconds of each
        other
        """
        self.client = client or MetricServiceClient()
        if not project_id:
            _, self.project_id = google.auth.default()
        else:
            self.project_id = project_id
        self.project_name = self.client.project_path(self.project_id)
        self._metric_descriptors = {}
        self._last_updated = {}
        self.add_unique_identifier = add_unique_identifier

    def _add_resource_info(self, series: TimeSeries) -> None:
        """Add Google resource specific information (e.g. instance id, region).

        Args:
            series: ProtoBuf TimeSeries
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
        instrument = record.instrument
        descriptor_type = "custom.googleapis.com/OpenTelemetry/{}".format(
            instrument.name
        )
        if descriptor_type in self._metric_descriptors:
            return self._metric_descriptors[descriptor_type]
        descriptor = {
            "name": None,
            "type": descriptor_type,
            "display_name": instrument.name,
            "description": instrument.description,
            "labels": [],
        }
        for key, value in record.labels:
            if isinstance(value, str):
                descriptor["labels"].append(
                    LabelDescriptor(key=key, value_type="STRING")
                )
            elif isinstance(value, bool):
                descriptor["labels"].append(
                    LabelDescriptor(key=key, value_type="BOOL")
                )
            elif isinstance(value, int):
                descriptor["labels"].append(
                    LabelDescriptor(key=key, value_type="INT64")
                )
            else:
                logger.warning(
                    "Label value %s is not a string, bool or integer", value
                )
        if isinstance(record.aggregator, SumAggregator):
            descriptor["metric_kind"] = MetricDescriptor.MetricKind.GAUGE
        else:
            logger.warning(
                "Unsupported aggregation type %s, ignoring it",
                type(record.aggregator).__name__,
            )
            return None
        if instrument.value_type == int:
            descriptor["value_type"] = MetricDescriptor.ValueType.INT64
        elif instrument.value_type == float:
            descriptor["value_type"] = MetricDescriptor.ValueType.DOUBLE
        proto_descriptor = MetricDescriptor(**descriptor)
        try:
            descriptor = self.client.create_metric_descriptor(
                self.project_name, proto_descriptor
            )
        # pylint: disable=broad-except
        except Exception as ex:
            logger.error(
                "Failed to create metric descriptor %s",
                proto_descriptor,
                exc_info=ex,
            )
            return None
        self._metric_descriptors[descriptor_type] = descriptor
        return descriptor

    def export(
        self, metric_records: Sequence[MetricRecord]
    ) -> "MetricsExportResult":
        all_series = []
        for record in metric_records:
            instrument = record.instrument
            metric_descriptor = self._get_metric_descriptor(record)
            if not metric_descriptor:
                continue

            series = TimeSeries()
            self._add_resource_info(series)
            series.metric.type = metric_descriptor.type
            for key, value in record.labels:
                series.metric.labels[key] = str(value)

            if self.add_unique_identifier:
                series.metric.labels["opentelemetry_uuid"] = uuid.uuid4().hex[
                    :8
                ]

            point = series.points.add()
            if instrument.value_type == int:
                point.value.int64_value = record.aggregator.checkpoint
            elif instrument.value_type == float:
                point.value.double_value = record.aggregator.checkpoint
            seconds, nanos = divmod(
                record.aggregator.last_update_timestamp, 1e9
            )

            # Cloud Monitoring API allows, for any combination of labels and
            # metric name, one update per WRITE_INTERVAL seconds
            updated_key = (metric_descriptor.type, record.labels)
            last_updated_seconds = self._last_updated.get(updated_key, 0)
            if seconds <= last_updated_seconds + WRITE_INTERVAL:
                continue
            self._last_updated[updated_key] = seconds
            point.interval.end_time.seconds = int(seconds)
            point.interval.end_time.nanos = int(nanos)
            all_series.append(series)
        try:
            self._batch_write(all_series)
        # pylint: disable=broad-except
        except Exception as ex:
            logger.error(
                "Error while writing to Cloud Monitoring", exc_info=ex
            )
            return MetricsExportResult.FAILURE
        return MetricsExportResult.SUCCESS
