# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import trace
from opentelemetry._logs import get_logger

# Once the count limit is reached, new attributes are dropped.
attributes = {"a": "abcdefgh", "b": 1, "dropped": 0}

with trace.get_tracer(__name__).start_as_current_span("limited-span", attributes=attributes):
    pass

get_logger(__name__).emit(body="limited log", attributes=attributes)
