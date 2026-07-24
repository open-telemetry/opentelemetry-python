# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import os
import time

from opentelemetry import _logs, metrics, trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    OTLPLogExporter,
)
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

os.environ.setdefault("OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED", "true")

resource = Resource.create({"service.name": "sdk-metrics-example"})

meter_provider = MeterProvider(resource=resource)
metrics.set_meter_provider(meter_provider)

# Pass the metrics provider into each SDK component that should report
# internal health metrics.
metric_exporter = OTLPMetricExporter(meter_provider=meter_provider)
metric_reader = PeriodicExportingMetricReader(
    metric_exporter,
    export_interval_millis=250,
)
meter_provider.add_metric_reader(metric_reader)

tracer_provider = TracerProvider(
    resource=resource,
    meter_provider=meter_provider,
)
tracer_provider.add_span_processor(
    SimpleSpanProcessor(
        OTLPSpanExporter(meter_provider=meter_provider),
        meter_provider=meter_provider,
    )
)
trace.set_tracer_provider(tracer_provider)

logger_provider = LoggerProvider(
    resource=resource,
    meter_provider=meter_provider,
)
logger_provider.add_log_record_processor(
    SimpleLogRecordProcessor(
        OTLPLogExporter(meter_provider=meter_provider),
        meter_provider=meter_provider,
    )
)
_logs.set_logger_provider(logger_provider)

tracer = trace.get_tracer(__name__)
logger = _logs.get_logger(__name__)

with tracer.start_as_current_span("example-span"):
    logger.emit(body="example log record")
    # Let the periodic reader export at least once so exporter self-metrics
    # are available for the final metrics export.
    time.sleep(0.5)

tracer_provider.force_flush()
logger_provider.force_flush()
meter_provider.force_flush()

tracer_provider.shutdown()
logger_provider.shutdown()
meter_provider.shutdown()
