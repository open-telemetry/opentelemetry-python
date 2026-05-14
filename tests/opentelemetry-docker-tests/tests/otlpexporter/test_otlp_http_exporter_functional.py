# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.test.test_base import TestBase

from . import BaseTestOTLPExporter, ExportStatusSpanProcessor


class TestOTLPHTTPExporter(BaseTestOTLPExporter, TestBase):
    # pylint: disable=no-self-use
    def get_span_processor(self):
        return ExportStatusSpanProcessor(OTLPSpanExporter())

    def setUp(self):
        super().setUp()

        trace.set_tracer_provider(TracerProvider())
        self.tracer = trace.get_tracer(__name__)
        self.span_processor = self.get_span_processor()

        trace.get_tracer_provider().add_span_processor(self.span_processor)
