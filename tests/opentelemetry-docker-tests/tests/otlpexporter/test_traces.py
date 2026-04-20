# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import time
import unittest

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Link, SpanKind, StatusCode

from . import TRACE_EXPORTERS, ExportStatusSpanProcessor


def _setup(factory):
    provider = TracerProvider()
    processor = ExportStatusSpanProcessor(factory())
    provider.add_span_processor(processor)
    tracer = provider.get_tracer(
        "test.tracer", "0.1.0", schema_url="https://example.com"
    )
    return provider, processor, tracer


class TestTraceExport(unittest.TestCase):
    def test_nested_spans(self):
        """Parent-child hierarchy with three levels."""
        for protocol, factory in TRACE_EXPORTERS:
            with self.subTest(protocol=protocol):
                provider, processor, tracer = _setup(factory)

                with tracer.start_as_current_span("foo"):
                    with tracer.start_as_current_span("bar"):
                        with tracer.start_as_current_span("baz"):
                            pass

                self.assertEqual(len(processor.export_status), 3)
                for status in processor.export_status:
                    self.assertEqual(status.name, "SUCCESS")

                provider.shutdown()

    def test_span_attributes(self):
        """Span with all supported attribute value types."""
        for protocol, factory in TRACE_EXPORTERS:
            with self.subTest(protocol=protocol):
                provider, processor, tracer = _setup(factory)

                with tracer.start_as_current_span("attrs") as span:
                    span.set_attribute("str_key", "value")
                    span.set_attribute("int_key", 42)
                    span.set_attribute("float_key", 3.14)
                    span.set_attribute("bool_key", True)
                    span.set_attribute("str_list", ["a", "b", "c"])
                    span.set_attribute("int_list", [1, 2, 3])
                    span.set_attribute("float_list", [1.1, 2.2])
                    span.set_attribute("bool_list", [True, False])

                self.assertEqual(processor.export_status[0].name, "SUCCESS")
                provider.shutdown()

    def test_span_events(self):
        """Span with events, including attributes and explicit timestamps."""
        for protocol, factory in TRACE_EXPORTERS:
            with self.subTest(protocol=protocol):
                provider, processor, tracer = _setup(factory)

                with tracer.start_as_current_span("events") as span:
                    span.add_event("simple_event")
                    span.add_event(
                        "event_with_attrs",
                        attributes={"event_key": "event_val", "count": 5},
                    )
                    span.add_event(
                        "timed_event",
                        timestamp=int(time.time_ns()),
                        attributes={"timed": True},
                    )

                self.assertEqual(processor.export_status[0].name, "SUCCESS")
                provider.shutdown()

    def test_span_links(self):
        """Span created with links to other span contexts."""
        for protocol, factory in TRACE_EXPORTERS:
            with self.subTest(protocol=protocol):
                provider, processor, tracer = _setup(factory)

                with tracer.start_as_current_span("link_target") as target:
                    target_ctx = target.get_span_context()

                link = Link(target_ctx, attributes={"link.reason": "related"})
                with tracer.start_as_current_span("linked", links=[link]):
                    pass

                for status in processor.export_status:
                    self.assertEqual(status.name, "SUCCESS")

                provider.shutdown()

    def test_span_status(self):
        """Spans with OK and ERROR status codes."""
        for protocol, factory in TRACE_EXPORTERS:
            with self.subTest(protocol=protocol):
                provider, processor, tracer = _setup(factory)

                with tracer.start_as_current_span("ok_span") as span:
                    span.set_status(StatusCode.OK)

                with tracer.start_as_current_span("error_span") as span:
                    span.set_status(
                        StatusCode.ERROR, description="something failed"
                    )

                for status in processor.export_status:
                    self.assertEqual(status.name, "SUCCESS")

                provider.shutdown()

    def test_span_kinds(self):
        """One span for each SpanKind variant."""
        for protocol, factory in TRACE_EXPORTERS:
            with self.subTest(protocol=protocol):
                provider, processor, tracer = _setup(factory)

                for kind in SpanKind:
                    with tracer.start_as_current_span(
                        f"span_{kind.name}", kind=kind
                    ):
                        pass

                for status in processor.export_status:
                    self.assertEqual(status.name, "SUCCESS")

                provider.shutdown()

    def test_record_exception(self):
        """Span that records an exception as an event."""
        for protocol, factory in TRACE_EXPORTERS:
            with self.subTest(protocol=protocol):
                provider, processor, tracer = _setup(factory)

                with tracer.start_as_current_span("exception_span") as span:
                    try:
                        raise ValueError("test error")
                    except ValueError as exc:
                        span.record_exception(exc)
                        span.set_status(StatusCode.ERROR, description=str(exc))

                self.assertEqual(processor.export_status[0].name, "SUCCESS")
                provider.shutdown()

    def test_resource_attributes(self):
        """Spans exported from a provider with custom resource."""
        for protocol, factory in TRACE_EXPORTERS:
            with self.subTest(protocol=protocol):
                resource = Resource.create(
                    {"service.name": "test-svc", "service.version": "1.0.0"}
                )
                provider = TracerProvider(resource=resource)
                processor = ExportStatusSpanProcessor(factory())
                provider.add_span_processor(processor)
                tracer = provider.get_tracer("test.tracer")

                with tracer.start_as_current_span("resource_span"):
                    pass

                self.assertEqual(processor.export_status[0].name, "SUCCESS")
                provider.shutdown()
