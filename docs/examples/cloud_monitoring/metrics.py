import sys
import time

from opentelemetry import metrics
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter
from opentelemetry.ext.cloud_monitoring import CloudMonitoringMetricsExporter
from opentelemetry.sdk.metrics.export.controller import PushController
from opentelemetry.context import attach, detach, set_value

metrics.set_meter_provider(MeterProvider())
meter = metrics.get_meter(__name__, True)
exporter = ConsoleMetricsExporter()
cloud_exporter = CloudMonitoringMetricsExporter("aaxue-starter")

exporters = [cloud_exporter]

staging_labels = {"environment": "staging"}
other_labels = {"label1": "s", "label2": "b"}

requests_counter = meter.create_metric(
    name="num_requests",
    description="number of requests",
    unit="1",
    value_type=int,
    metric_type=Counter,
    label_keys=("environment",),
)

double_counter = meter.create_metric(
    name="doublly",
    description="double",
    unit="unit double name",
    value_type=float,
    metric_type=Counter,
    label_keys=("label1", "label1"),
)


def _ghetto_export():
    for exporter in exporters:
        meter.collect()
        token = attach(set_value("suppress_instrumentation", True))
        to_export = meter.batcher.checkpoint_set()
        exporter.export(to_export)
        detach(token)
        # Perform post-exporting logic based on batcher configuration
        meter.batcher.finished_collection()

for i in range(20):
    requests_counter.add(25, staging_labels)
    double_counter.add(2.3, other_labels)
    _ghetto_export()
    time.sleep(10)
    requests_counter.add(20, staging_labels)
    double_counter.add(2.53, other_labels)
    _ghetto_export()
