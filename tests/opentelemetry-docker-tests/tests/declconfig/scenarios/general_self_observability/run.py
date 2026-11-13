# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import contextlib
import threading

from opentelemetry import trace

tracer = trace.get_tracer(__name__)

for _ in range(3):
    with tracer.start_as_current_span("self-obs-span"):
        pass

# The metric exporter's and reader's own metrics are only reported on the next
# collection, so stay alive for the periodic reader until the harness stops
# the app.
with contextlib.suppress(KeyboardInterrupt):
    threading.Event().wait()
