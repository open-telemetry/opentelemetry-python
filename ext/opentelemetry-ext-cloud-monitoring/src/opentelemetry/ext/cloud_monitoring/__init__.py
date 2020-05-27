from typing import Sequence

from google.cloud.monitoring_v3 import MetricServiceClient
from google.cloud.monitoring_v3.proto.metric_pb2 import TimeSeries
from opentelemetry.sdk.metrics.export import (
    MetricsExporter,
    MetricRecord,
    MetricsExportResult,
)

MAX_BATCH_WRITE = 200


class CloudMonitoringMetricsExporter(MetricsExporter):
    """
    Implementation of Metrics Exporter that sends metrics to Google Cloud
    Monitoring
    """

    def __init__(self, project_id, client=None):
        self.client = client or MetricServiceClient()
        self.project_id = project_id
        self.project_name = self.client.project_path(project_id)
        self._last_updated = {}

    def _add_resource_info(self, series):
        """ Add Google resource specific information (e.g. instance id, region)

        :param series: ProtoBuf TimeSeries
        :return:
        """
        series.resource.type = "gce_instance"
        series.resource.labels["instance_id"] = "1234567890123456789"
        series.resource.labels["zone"] = "us-central1-f"

    def _batch_write(self, series):
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

    def export(
        self, metric_records: Sequence[MetricRecord]
    ) -> "MetricsExportResult":
        all_series = []
        for record in metric_records:
            recorded_metric = record.metric
            aggregated_metric = record.aggregator
            series_name = "custom.googleapis.com/OpenTelemetry/{}".format(
                recorded_metric.name
            )
            series = TimeSeries()
            self._add_resource_info(series)
            series.metric.type = series_name
            for k, v in record.labels:
                series.metric.labels[k] = v
            point = series.points.add()
            if recorded_metric.value_type == int:
                point.value.int64_value = aggregated_metric.checkpoint
            elif recorded_metric.value_type == float:
                point.value.double_value = aggregated_metric.checkpoint
            seconds, nanos = divmod(
                aggregated_metric.last_update_timestamp, 1e9
            )

            # Cloud Monitoring allows every timeseries to be updated one per
            # minute at most
            if seconds - self._last_updated.get(series_name, 0) < 60:
                continue
            self._last_updated[series.metric.type] = seconds
            point.interval.end_time.seconds = int(seconds)
            point.interval.end_time.nanos = int(nanos)
            all_series.append(series)
            print("will write {} to {}".format(point, series.metric.type))
        self._batch_write(all_series)
        print("wrote to cloud monitorint")
        return MetricsExportResult.SUCCESS
