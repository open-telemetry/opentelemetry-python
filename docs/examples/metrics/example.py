from opentelemetry._metrics import set_meter_provider, get_meter_provider
from opentelemetry.exporter.otlp.proto.grpc._metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.sdk._metrics import MeterProvider


provider = MeterProvider()
exporter = OTLPMetricExporter(insecure=True)
# TODO: fill in details for metric reader
set_meter_provider(provider)

meter = get_meter_provider().get_meter("getting-started")
counter = meter.create_counter("first_counter")
# TODO: fill in details for additional metrics
