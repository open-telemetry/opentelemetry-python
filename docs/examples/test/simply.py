
import requests
from opentelemetry.metrics import (
    set_meter_provider,
)
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader

exporter = ConsoleMetricExporter()
reader = PeriodicExportingMetricReader(exporter, export_interval_millis=60000)
provider = MeterProvider(metric_readers=[reader])
set_meter_provider(provider)

RequestsInstrumentor().instrument(meter_provider=provider)

response = requests.get(url="https://www.example.org/")
