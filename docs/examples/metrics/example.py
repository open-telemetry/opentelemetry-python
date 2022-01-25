from opentelemetry._metrics import get_meter_provider, set_meter_provider
from opentelemetry.exporter.otlp.proto.grpc._metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.sdk._metrics import MeterProvider
from opentelemetry.sdk._metrics.export import PeriodicExportingMetricReader

exporter = OTLPMetricExporter(insecure=True)
reader = PeriodicExportingMetricReader(exporter)
provider = MeterProvider(metric_readers=[reader])
set_meter_provider(provider)

meter = get_meter_provider().get_meter("getting-started")
counter = meter.create_counter("first_counter")
counter.add(1)
# TODO: fill in details for additional metrics
