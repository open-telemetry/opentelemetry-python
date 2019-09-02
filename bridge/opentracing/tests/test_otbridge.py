# Copyright 2019, OpenTelemetry Authors
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

import unittest

import opentracing
from opentracing.ext import tags
from opentracing.propagation import Format

from opentelemetry.sdk.trace import Span as OtelSpan
from opentelemetry.trace import SpanContext as OtelSpanContext
from ot_otel_bridge.span import BridgeSpan
from ot_otel_bridge.tracer import tracer


class TestOTBridge(unittest.TestCase):
    def setUp(self):
        opentracing.tracer = tracer()

    def test_basic(self):
        with opentracing.tracer.start_active_span("TestBasic") as scope:
            self.assertIsInstance(scope.span, opentracing.Span)
            self.assertIsInstance(scope.span, BridgeSpan)
            self.assertIsInstance(scope.span.otel_span, OtelSpan)
            self.assertIsInstance(
                scope.span.otel_span.get_context(), OtelSpanContext
            )

    def test_name(self):
        with opentracing.tracer.start_active_span("TestName") as scope:
            self.assertEqual(scope.span.otel_span.name, "TestName")
            scope.span.set_operation_name("NewName")
            self.assertEqual(scope.span.otel_span.name, "NewName")

    def test_tags(self):
        with opentracing.tracer.start_active_span("TestTags") as scope:
            scope.span.set_tag("my_tag_key", "my_tag_value")
            self.assertTrue("my_tag_key" in scope.span.otel_span.attributes)
            self.assertEqual(
                scope.span.otel_span.attributes["my_tag_key"], "my_tag_value"
            )

    def test_baggage(self):
        # TODO: At the moment, the bridge does not do anything with the baggage
        # so this is just checking for consistency.
        with opentracing.tracer.start_active_span("TestBaggage") as scope:
            scope.span.set_baggage_item("my_baggage_item", "the_baggage")
            self.assertEqual(
                scope.span.get_baggage_item("my_baggage_item"), "the_baggage"
            )

    def test_log(self):
        # TODO: At the moment, the bridge does not do anything with logs
        with opentracing.tracer.start_active_span("TestLog") as scope:
            scope.span.log_kv({"event": "string-format", "value": "the_log"})
            scope.span.log_event("message", payload={"number": 42})
            scope.span.log_event("message", payload={"number": 43})
            self.assertEqual(len(scope.span.logs), 3)

    def test_subspan(self):
        with opentracing.tracer.start_active_span("TestGrandparent") as scope1:
            with opentracing.tracer.start_active_span("TestParent") as scope2:
                with opentracing.tracer.start_active_span(
                    "TestChild"
                ) as scope3:
                    ctx1 = scope1.span.otel_span.get_context()
                    ctx2 = scope2.span.otel_span.get_context()
                    ctx3 = scope3.span.otel_span.get_context()

                    self.assertEqual(ctx1.trace_id, ctx2.trace_id)
                    self.assertEqual(ctx1.trace_id, ctx3.trace_id)

                    self.assertEqual(
                        ctx1.span_id, scope2.span.otel_span.parent.span_id
                    )
                    self.assertEqual(
                        ctx2.span_id, scope3.span.otel_span.parent.span_id
                    )

                    self.assertNotEqual(ctx1.span_id, ctx2.span_id)
                    self.assertNotEqual(ctx1.span_id, ctx3.span_id)

    def test_inject_extract(self):
        headers = {}
        with opentracing.tracer.start_active_span("ClientSide") as scope:
            client_ctx = scope.span.otel_span.get_context()
            opentracing.tracer.inject(
                scope.span.context, Format.HTTP_HEADERS, headers
            )

        span_ctx = opentracing.tracer.extract(Format.HTTP_HEADERS, headers)
        span_tags = {tags.SPAN_KIND: tags.SPAN_KIND_RPC_SERVER}
        with opentracing.tracer.start_active_span(
            "ServerSide", child_of=span_ctx, tags=span_tags
        ) as scope:
            server_ctx = scope.span.otel_span.get_context()
            self.assertEqual(client_ctx.trace_id, server_ctx.trace_id)
            self.assertEqual(
                client_ctx.trace_id, scope.span.otel_span.parent.trace_id
            )
            self.assertEqual(
                client_ctx.span_id, scope.span.otel_span.parent.span_id
            )
