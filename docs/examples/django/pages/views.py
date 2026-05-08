# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
from django.http import HttpResponse

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)

trace.set_tracer_provider(TracerProvider())

trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(ConsoleSpanExporter())
)


def home_page_view(request):
    return HttpResponse("Hello, world")
