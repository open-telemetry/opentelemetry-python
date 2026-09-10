# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Prototype of the "Span type" OTEP.

Sets a span type at span creation and shows how it reaches the OTLP gRPC
exporter. Until OTLP has a top-level ``Span.type`` field, the exporter emits it
as the ``otel.span.type`` attribute.

Run with a collector on localhost:4317, or without one to just see the encoded
payload.
"""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.common._internal.trace_encoder import (
    encode_spans,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

captured: list = []


class _Capture(SimpleSpanProcessor):
    def on_end(self, span):
        captured.append(span)
        super().on_end(span)


provider = TracerProvider()
provider.add_span_processor(_Capture(OTLPSpanExporter(insecure=True)))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span(
    "chat gpt-4o-mini",
    kind=trace.SpanKind.CLIENT,
    span_type="gen_ai.client.inference",
    attributes={"gen_ai.operation.name": "chat"},
) as span:
    # span type is immutable: readable from the SDK span, no setter exists
    print("span_type on the SDK span:", span.span_type)

provider.force_flush()

print("\nOTLP payload:")
print(encode_spans(captured))
