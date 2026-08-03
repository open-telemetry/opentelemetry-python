# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import Mock, patch

from opentelemetry.exporter.otlp._proto.http.trace_exporter import (
    OTLPSpanExporter as PyprotoSpanExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
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


def test_http_serialized_payload_matches_proto():
    spans = _sample_spans()

    proto_exporter = ProtoSpanExporter()
    with patch("requests.Session.post") as proto_post:
        proto_post.return_value = Mock(ok=True, status_code=200)
        proto_exporter.export(spans)
    proto_payload = proto_post.call_args.kwargs["data"]

    pyproto_exporter = PyprotoSpanExporter()
    with patch(
        "opentelemetry.exporter.otlp._proto.http.trace_exporter._post"
    ) as pyproto_post:
        pyproto_post.return_value = (200, "OK")
        pyproto_exporter.export(spans)
    pyproto_payload = pyproto_post.call_args.args[1]

    assert pyproto_payload == proto_payload
