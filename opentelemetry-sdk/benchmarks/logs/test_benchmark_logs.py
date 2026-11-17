# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import pytest

from opentelemetry._logs import LogRecord, SeverityNumber
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import (
    BatchLogRecordProcessor,
    InMemoryLogRecordExporter,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

resource = Resource(
    {
        "service.name": "A123456789",
        "service.version": "1.34567890",
        "service.instance.id": "123ab456-a123-12ab-12ab-12340a1abc12",
    }
)

simple_exporter = InMemoryLogRecordExporter()
simple_provider = LoggerProvider(resource=resource)
simple_provider.add_log_record_processor(SimpleLogRecordProcessor(simple_exporter))
simple_logger = simple_provider.get_logger("simple_logger")

batch_exporter = InMemoryLogRecordExporter()
batch_provider = LoggerProvider(resource=resource)
batch_provider.add_log_record_processor(BatchLogRecordProcessor(batch_exporter))
batch_logger = batch_provider.get_logger("batch_logger")


@pytest.mark.parametrize("num_attributes", [0, 1, 3, 5, 10])
def test_simple_log_record_processor(benchmark, num_attributes):
    attributes = {f"key{i}": f"value{i}" for i in range(num_attributes)}

    def benchmark_emit():
        simple_logger.emit(
            severity_number=SeverityNumber.INFO,
            body="benchmark log message",
            attributes=attributes,
            event_name="test.event",
        )

    benchmark(benchmark_emit)


@pytest.mark.parametrize("num_attributes", [0, 1, 3, 5, 10])
def test_batch_log_record_processor(benchmark, num_attributes):
    attributes = {f"key{i}": f"value{i}" for i in range(num_attributes)}

    def benchmark_emit():
        batch_logger.emit(
            severity_number=SeverityNumber.INFO,
            body="benchmark log message",
            attributes=attributes,
            event_name="test.event",
        )

    benchmark(benchmark_emit)


def test_get_logger(benchmark):
    def benchmark_get_logger():
        simple_provider.get_logger(
            "test_logger",
            version="1.0.0",
            schema_url="https://opentelemetry.io/schemas/1.38.0",
        )

    benchmark(benchmark_get_logger)


def test_emit_with_exception(benchmark):
    try:
        raise ValueError("benchmark exception")
    except ValueError as exc:
        exception = exc

    def benchmark_emit():
        simple_logger.emit(
            severity_number=SeverityNumber.ERROR,
            body="benchmark log message",
            # pylint: disable-next=used-before-assignment
            exception=exception,
        )

    benchmark(benchmark_emit)


def test_emit_in_active_span(benchmark):
    tracer = TracerProvider(resource=resource, shutdown_on_exit=False).get_tracer("benchmark_tracer")

    def benchmark_emit():
        simple_logger.emit(
            severity_number=SeverityNumber.INFO,
            body="benchmark log message",
            event_name="test.event",
        )

    with tracer.start_as_current_span("benchmark_span"):
        benchmark(benchmark_emit)


@pytest.mark.parametrize("style", ["kwargs", "log_record"])
def test_emit_log_record_vs_kwargs(benchmark, style):
    benchmark.group = "emit-log-record-vs-kwargs"
    attributes = {f"key{i}": f"value{i}" for i in range(5)}

    def benchmark_emit_kwargs():
        simple_logger.emit(
            severity_number=SeverityNumber.INFO,
            body="benchmark log message",
            attributes=attributes,
            event_name="test.event",
        )

    def benchmark_emit_log_record():
        simple_logger.emit(
            LogRecord(
                severity_number=SeverityNumber.INFO,
                body="benchmark log message",
                attributes=attributes,
                event_name="test.event",
            )
        )

    benchmark(benchmark_emit_kwargs if style == "kwargs" else benchmark_emit_log_record)
