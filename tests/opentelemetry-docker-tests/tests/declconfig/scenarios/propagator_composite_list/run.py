# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import baggage, propagate, trace

tracer = trace.get_tracer(__name__)

carrier: dict[str, str] = {}
with tracer.start_as_current_span("outgoing"):
    propagate.inject(carrier, context=baggage.set_baggage("user.id", "u-123"))

extracted = propagate.extract(carrier)
attributes = {
    "carrier.keys": ",".join(sorted(carrier)) or "<none>",
    "baggage.user.id": str(baggage.get_baggage("user.id", extracted) or "<none>"),
}
with tracer.start_as_current_span("incoming", context=extracted, attributes=attributes):
    pass
