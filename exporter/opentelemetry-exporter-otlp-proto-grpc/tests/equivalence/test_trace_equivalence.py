# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import patch

from opentelemetry.exporter.otlp._proto.grpc.trace_exporter import (
    OTLPSpanExporter as PyprotoSpanExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as ProtoSpanExporter,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter


def _sample_spans():
    captured = []

    class _Capture(SpanExporter):
        def export(self, spans):
            captured.extend(spans)
            return 0

        def shutdown(self):
            pass

    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(_Capture()))
    tracer = provider.get_tracer("equivalence")
    with tracer.start_as_current_span("op") as span:
        span.set_attribute("str", "v")
        span.set_attribute("int", 7)
        span.set_attribute("bool", True)
    return list(captured)


def test_grpc_serialized_request_matches_proto():
    spans = _sample_spans()

    with patch(
        "opentelemetry.exporter.otlp.proto.grpc.exporter.insecure_channel"
    ):
        proto_exporter = ProtoSpanExporter(insecure=True)
    proto_bytes = proto_exporter._translate_data(spans).SerializeToString()

    with patch(
        "opentelemetry.exporter.otlp._proto.grpc.exporter.insecure_channel"
    ):
        pyproto_exporter = PyprotoSpanExporter(insecure=True)
    pyproto_bytes = pyproto_exporter._translate_data(spans).SerializeToString()

    assert pyproto_bytes == proto_bytes
