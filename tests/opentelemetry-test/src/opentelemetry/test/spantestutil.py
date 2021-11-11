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
from functools import partial
from importlib import reload

from opentelemetry import trace as trace_api
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.trace import Resource, TracerProvider, export
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

_MEMORY_EXPORTER = None


def new_tracer(span_limits=None, resource=None) -> trace_api.Tracer:
    provider_factory = trace_sdk.TracerProvider
    if resource is not None:
        provider_factory = partial(provider_factory, resource=resource)
    return provider_factory(span_limits=span_limits).get_tracer(__name__)


class SpanTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global _MEMORY_EXPORTER  # pylint:disable=global-statement
        trace_api.set_tracer_provider(TracerProvider())
        tracer_provider = trace_api.get_tracer_provider()
        _MEMORY_EXPORTER = InMemorySpanExporter()
        span_processor = export.SimpleSpanProcessor(_MEMORY_EXPORTER)
        tracer_provider.add_span_processor(span_processor)

    @classmethod
    def tearDownClass(cls):
        reload(trace_api)

    def setUp(self):
        self.memory_exporter = _MEMORY_EXPORTER
        self.memory_exporter.clear()


def get_span_with_dropped_attributes_events_links():
    attributes = {}
    for index in range(130):
        attributes[f"key{index}"] = [f"value{index}"]
    links = []
    for index in range(129):
        links.append(
            trace_api.Link(
                trace_sdk._Span(
                    name=f"span{index}",
                    context=trace_api.INVALID_SPAN_CONTEXT,
                    attributes=attributes,
                ).get_span_context(),
                attributes=attributes,
            )
        )

    tracer = new_tracer(
        span_limits=trace_sdk.SpanLimits(),
        resource=Resource(attributes=attributes),
    )
    with tracer.start_as_current_span(
        "span", links=links, attributes=attributes
    ) as span:
        for index in range(131):
            span.add_event(f"event{index}", attributes=attributes)
        return span
