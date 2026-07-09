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
    BatchSpanProcessor,
    ConsoleSpanExporter,
)


def main():
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "instrumentation_example.settings"
    )

    # Set up tracing with console exporter to see spans in stdout
    trace.set_tracer_provider(TracerProvider())
    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(ConsoleSpanExporter())
    )

    # This call is what makes the Django application be instrumented
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
