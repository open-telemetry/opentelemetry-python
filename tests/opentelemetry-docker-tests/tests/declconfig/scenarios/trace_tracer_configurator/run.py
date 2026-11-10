# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import trace

with trace.get_tracer("enabled.lib").start_as_current_span("enabled-span"):
    pass
with trace.get_tracer("disabled.lib").start_as_current_span("disabled-span"):
    pass
