import time

from opentelemetry import metrics
from opentelemetry.exporter.cloud_monitoring import (
    CloudMonitoringMetricsExporter,
)
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export.controller import PushController

metrics.set_meter_provider(MeterProvider())
meter = metrics.get_meter(__name__, True)

# Gather and export metrics every 5 seconds
controller = PushController(
    meter=meter, exporter=CloudMonitoringMetricsExporter(), interval=5
)

requests_counter = meter.create_metric(
    name="request_counter",
    description="number of requests",
    unit="1",
    value_type=int,
    metric_type=Counter,
    label_keys=("environment"),
)

staging_labels = {"environment": "staging"}

for i in range(20):
    requests_counter.add(25, staging_labels)
    time.sleep(10)
