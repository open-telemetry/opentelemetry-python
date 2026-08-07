#!/usr/bin/env python
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Django"s command-line utility for administrative tasks."""

import os
import sys

from opentelemetry import trace
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "instrumentation_example.settings")

    # Set up a tracer provider with a console exporter so that the spans
    # generated below are printed to stdout. Comment out this block when
    # running with auto instrumentation (``opentelemetry-instrument``), which
    # configures the tracer provider and exporter for you.
    trace.set_tracer_provider(TracerProvider())
    trace.get_tracer_provider().add_span_processor(
        SimpleSpanProcessor(ConsoleSpanExporter())
    )

    # This call is what makes the Django application be instrumented.
    # Comment it out when running with auto instrumentation.
    DjangoInstrumentor().instrument()

    try:
        from django.core.management import (  # noqa: PLC0415
            execute_from_command_line,
        )
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
