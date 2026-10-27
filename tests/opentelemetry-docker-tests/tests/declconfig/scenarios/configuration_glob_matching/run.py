# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import metrics, trace
from opentelemetry._logs import get_logger

# Literal brackets, bracket-class lookalikes, case sensitivity, and '?' width.
for scope in ("disabled[bc]", "disabledb", "wild[bc].x", "wildb.x", "Disabled[bc]", "wild[bc].xx"):
    with trace.get_tracer(scope).start_as_current_span("scope-span", attributes={"route": "keep[bc]"}):
        pass
    metrics.get_meter(scope).create_counter("glob.requests").add(1)
    get_logger(scope).emit(body="scope-log")

# Only the first two routes should pass the configured include/exclude patterns.
for name, route in (
    ("sampler-exact", "keep[bc]"),
    ("sampler-wildcard", "keep[bc].child"),
    ("sampler-class", "keepb"),
    ("sampler-excluded", "keep[bc].drop"),
    ("sampler-excluded-wildcard", "keep[bc].secret"),
    ("sampler-case", "Keep[bc]"),
):
    with trace.get_tracer("sampler").start_as_current_span(name, attributes={"route": route}):
        pass
