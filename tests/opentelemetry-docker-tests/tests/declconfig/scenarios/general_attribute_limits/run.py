# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import trace
from opentelemetry._logs import get_logger

# Once the count limit is reached, the oldest attribute is dropped.
attributes = {"dropped": 0, "a": "abcdefgh", "b": 1}

with trace.get_tracer(__name__).start_as_current_span("limited-span", attributes=attributes):
    pass

get_logger(__name__).emit(body="limited log", attributes=attributes)
