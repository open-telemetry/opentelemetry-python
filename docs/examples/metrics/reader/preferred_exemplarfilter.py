# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
import time

from opentelemetry import trace
from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.exemplar import AlwaysOnExemplarFilter
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.trace import TracerProvider

# Create an ExemplarFilter instance
# Available values are AlwaysOffExemplarFilter, AlwaysOnExemplarFilter
# and TraceBasedExemplarFilter.
# The default value is `TraceBasedExemplarFilter`.
#
# You can also use the environment variable `OTEL_METRICS_EXEMPLAR_FILTER`
# to change the default value.
#
# You can also define your own filter by implementing the abstract class
# `ExemplarFilter`
exemplar_filter = AlwaysOnExemplarFilter()

exporter = ConsoleMetricExporter()

reader = PeriodicExportingMetricReader(
    exporter,
    export_interval_millis=5_000,
)

# Set up the MeterProvider with the ExemplarFilter
provider = MeterProvider(
    metric_readers=[reader],
    exemplar_filter=exemplar_filter,  # Pass the ExemplarFilter to the MeterProvider
)
set_meter_provider(provider)

meter = get_meter_provider().get_meter("exemplar-filter-example", "0.1.2")
counter = meter.create_counter("my-counter")

# Create a trace and span as the default exemplar filter `TraceBasedExemplarFilter`
# will only store exemplar if a context exists
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("foo"):
    for value in range(10):
        counter.add(value)
        time.sleep(2.0)
