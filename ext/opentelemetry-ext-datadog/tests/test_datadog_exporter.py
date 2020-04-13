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

import unittest
from unittest import mock

from ddtrace.internal.writer import AgentWriter

# pylint:disable=no-name-in-module
# pylint:disable=import-error
import opentelemetry.ext.datadog as datadog_exporter
from opentelemetry import trace as trace_api
from opentelemetry.sdk import trace


class TestDatadogSpanExporter(unittest.TestCase):
    def test_constructor_default(self):
        """Test the default values assigned by constructor."""
        exporter = datadog_exporter.DatadogSpanExporter()

        self.assertEqual(exporter.agent_url, "http://localhost:8126")
        self.assertTrue(exporter.service is None)
        self.assertTrue(exporter.agent_writer is not None)

    def test_constructor_explicit(self):
        """Test the constructor passing all the options."""
        agent_url = "http://localhost:8126"
        exporter = datadog_exporter.DatadogSpanExporter(
            agent_url=agent_url, service="explicit"
        )

        self.assertEqual(exporter.agent_url, agent_url)
        self.assertEqual(exporter.service, "explicit")
        self.assertTrue(exporter.agent_writer is not None)

    @mock.patch.dict(
        "os.environ",
        {"DD_TRACE_AGENT_URL": "http://agent:8126", "DD_SERVICE": "environ"},
    )
    def test_constructor_environ(self):
        exporter = datadog_exporter.DatadogSpanExporter()

        self.assertEqual(exporter.agent_url, "http://agent:8126")
        self.assertEqual(exporter.service, "environ")
        self.assertTrue(exporter.agent_writer is not None)

    # pylint: disable=too-many-locals
    @mock.patch.dict("os.environ", {"DD_SERVICE": "test-service"})
    def test_translate_to_datadog(self):
        # pylint: disable=invalid-name
        self.maxDiff = None

        span_names = ("test1", "test2", "test3")
        trace_id = 0x6E0C63257DE34C926F9EFCD03927272E
        trace_id_low = 0x6F9EFCD03927272E
        span_id = 0x34BF92DEEFC58C92
        parent_id = 0x1111111111111111
        other_id = 0x2222222222222222

        base_time = 683647322 * 10 ** 9  # in ns
        start_times = (
            base_time,
            base_time + 150 * 10 ** 6,
            base_time + 300 * 10 ** 6,
        )
        durations = (50 * 10 ** 6, 100 * 10 ** 6, 200 * 10 ** 6)
        end_times = (
            start_times[0] + durations[0],
            start_times[1] + durations[1],
            start_times[2] + durations[2],
        )

        span_context = trace_api.SpanContext(
            trace_id, span_id, is_remote=False
        )
        parent_context = trace_api.SpanContext(
            trace_id, parent_id, is_remote=False
        )
        other_context = trace_api.SpanContext(
            trace_id, other_id, is_remote=False
        )

        otel_spans = [
            trace.Span(
                name=span_names[0],
                context=span_context,
                parent=parent_context,
                kind=trace_api.SpanKind.CLIENT,
            ),
            trace.Span(
                name=span_names[1], context=parent_context, parent=None
            ),
            trace.Span(name=span_names[2], context=other_context, parent=None),
        ]

        otel_spans[0].start(start_time=start_times[0])
        otel_spans[0].end(end_time=end_times[0])

        otel_spans[1].start(start_time=start_times[1])
        otel_spans[1].end(end_time=end_times[1])

        otel_spans[2].start(start_time=start_times[2])
        otel_spans[2].end(end_time=end_times[2])

        # pylint: disable=protected-access
        exporter = datadog_exporter.DatadogSpanExporter()
        datadog_spans = [
            span.to_dict()
            for span in exporter._translate_to_datadog(otel_spans)
        ]

        expected_spans = [
            dict(
                trace_id=trace_id_low,
                parent_id=parent_id,
                span_id=span_id,
                name=span_names[0],
                resource=span_names[0],
                start=start_times[0],
                duration=durations[0],
                error=0,
                service="test-service",
            ),
            dict(
                trace_id=trace_id_low,
                parent_id=0,
                span_id=parent_id,
                name=span_names[1],
                resource=span_names[1],
                start=start_times[1],
                duration=durations[1],
                error=0,
                service="test-service",
            ),
            dict(
                trace_id=trace_id_low,
                parent_id=0,
                span_id=other_id,
                name=span_names[2],
                resource=span_names[2],
                start=start_times[2],
                duration=durations[2],
                error=0,
                service="test-service",
            ),
        ]

        self.assertEqual(datadog_spans, expected_spans)

    @mock.patch.dict("os.environ", {"DD_SERVICE": "test-service"})
    def test_export(self):
        """Test that agent and/or collector are invoked"""
        exporter = datadog_exporter.DatadogSpanExporter()

        # just agent is configured now
        agent_writer_mock = mock.Mock(spec=AgentWriter)
        # pylint: disable=protected-access
        exporter._agent_writer = agent_writer_mock

        # create and save span to be used in tests
        context = trace_api.SpanContext(
            trace_id=0x000000000000000000000000DEADBEEF,
            span_id=0x00000000DEADBEF0,
            is_remote=False,
        )

        test_span = trace.Span("test_span", context=context)
        test_span.start()
        test_span.end()

        exporter.export((test_span,))

        self.assertEqual(agent_writer_mock.write.call_count, 1)
