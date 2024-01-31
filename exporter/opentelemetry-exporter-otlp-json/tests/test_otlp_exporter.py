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
import json

from opentelemetry import trace
from opentelemetry.trace import TraceFlags
from opentelemetry.exporter.otlp.json import DEFAULT_ENDPOINT
from opentelemetry.exporter.otlp.json.traces_exporter import OTLPSpanExporter
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult

TEST_SERVICE_NAME = "test_service"


class MockResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = status_code


class TestOTLPSpanExporter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        trace.set_tracer_provider(
            TracerProvider(
                resource=Resource({SERVICE_NAME: TEST_SERVICE_NAME})
            )
        )

    
    def test_serialize(self):
        test_resource = Resource.create({SERVICE_NAME: TEST_SERVICE_NAME})
        test_scope = InstrumentationScope(
            name="name", version="version",
        ),
        trace_id = 0x6E0C63257DE34C926F9EFCD03927272E
        spans = [
            ReadableSpan(
                name="test-span-1",
                context=trace.SpanContext(
                    trace_id,
                    0x34BF92DEEFC58C92,
                    is_remote=False,
                    trace_flags=TraceFlags(TraceFlags.SAMPLED),
                ),
                resource=test_resource,
                instrumentation_scope=test_scope,
            )
        ]
        exporter = OTLPSpanExporter()
        encoded_data = exporter._serialize_spans(spans)
        print(encoded_data)

        expected_output = json.dumps({
            "resource_spans": [
                {
                    "resource": json.loads(spans[0].resource.to_json()),
                    "scope_spans": [
                        {
                            "scope": json.loads(spans[0].instrumentation_scope[0].to_json()),
                            "spans": [json.loads(spans[0].to_json())],
                        }
                    ],
                }
            ]
        })
        print(expected_output)
        self.assertEqual(encoded_data, expected_output)
