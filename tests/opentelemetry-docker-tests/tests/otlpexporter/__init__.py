# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from abc import ABC, abstractmethod

from opentelemetry.context import attach, detach, set_value
from opentelemetry.sdk.trace.export import SimpleSpanProcessor


class ExportStatusSpanProcessor(SimpleSpanProcessor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.export_status = []

    def on_end(self, span):
        token = attach(set_value("suppress_instrumentation", True))
        self.export_status.append(self.span_exporter.export((span,)))
        detach(token)


class BaseTestOTLPExporter(ABC):
    @abstractmethod
    def get_span_processor(self):
        pass

    # pylint: disable=no-member
    def test_export(self):
        with self.tracer.start_as_current_span("foo"):
            with self.tracer.start_as_current_span("bar"):
                with self.tracer.start_as_current_span("baz"):
                    pass

        self.assertTrue(len(self.span_processor.export_status), 3)

        for export_status in self.span_processor.export_status:
            self.assertEqual(export_status.name, "SUCCESS")
            self.assertEqual(export_status.value, 0)
