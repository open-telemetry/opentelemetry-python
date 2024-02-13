import random
import time

from prometheus_client import start_http_server

from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider

# Start Prometheus client
start_http_server(port=8000, addr="localhost")
# Exporter to export metrics to Prometheus
prefix = "MyAppPrefix"
reader = PrometheusMetricReader(prefix)
# Meter is responsible for creating and recording metrics
set_meter_provider(MeterProvider(metric_readers=[reader]))
meter = get_meter_provider().get_meter("view-name-change", "0.1.2")

my_counter = meter.create_counter("my.counter")

while 1:
    my_counter.add(random.randint(1, 10))
    time.sleep(random.random())
