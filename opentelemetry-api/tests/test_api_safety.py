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

from unittest import TestCase

from opentelemetry.attributes import BoundedAttributes
from opentelemetry.context.contextvars_context import ContextVarsRuntimeContext
from opentelemetry.context.context import Context
from opentelemetry.context import create_key
from opentelemetry.context import get_value
from opentelemetry.context import set_value
from opentelemetry.context import get_current
from opentelemetry.context import attach
from opentelemetry.context import detach
from opentelemetry.propagators.textmap import Getter
from opentelemetry.propagators.textmap import Setter
from opentelemetry.propagators.textmap import DefaultGetter
from opentelemetry.propagators.textmap import DefaultSetter
from opentelemetry.propagators.textmap import TextMapPropagator
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.propagators.composite import CompositeHTTPPropagator
from opentelemetry.baggage import get_all
from opentelemetry.baggage import get_baggage
from opentelemetry.baggage import set_baggage
from opentelemetry.baggage import remove_baggage
from opentelemetry.baggage import clear
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.util.re import parse_headers
from opentelemetry.propagate import extract
from opentelemetry.propagate import inject
from opentelemetry.propagate import get_global_textmap
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace.status import StatusCode
from opentelemetry.trace.span import Span
from opentelemetry.trace.span import NoOpSpan
from opentelemetry.trace.span import TraceFlags
from opentelemetry.trace.span import TraceState
from opentelemetry.trace.span import SpanContext
from opentelemetry.trace.span import NonRecordingSpan
from opentelemetry.trace.span import format_trace_id
from opentelemetry.trace.span import format_span_id
from opentelemetry.trace import Link
from opentelemetry.trace import SpanKind
from opentelemetry.trace import TracerProvider
from opentelemetry.trace import NoOpTracerProvider
from opentelemetry.trace import ProxyTracerProvider
from opentelemetry.trace import Tracer
from opentelemetry.trace import NoOpTracer
from opentelemetry.trace import ProxyTracer
from opentelemetry.trace import get_tracer
from opentelemetry.trace import set_tracer_provider
from opentelemetry.trace import get_tracer_provider
from opentelemetry.trace import use_span
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.trace.propagation import set_span_in_context
from opentelemetry.trace.propagation import get_current_span


ContextVarsRuntimeContext
Context
create_key
get_value
set_value
get_current
attach
detach
Getter
Setter
DefaultGetter
DefaultSetter
TextMapPropagator
CompositePropagator
CompositeHTTPPropagator
get_all
get_baggage
set_baggage
remove_baggage
clear
W3CBaggagePropagator
parse_headers
extract
inject
get_global_textmap
set_global_textmap
StatusCode
Span
NoOpSpan
TraceFlags
TraceState
SpanContext
NonRecordingSpan
format_trace_id
format_span_id
Link
SpanKind
TracerProvider
NoOpTracerProvider
ProxyTracerProvider
Tracer
NoOpTracer
ProxyTracer
get_tracer
set_tracer_provider
get_tracer_provider
use_span
TraceContextTextMapPropagator
set_span_in_context
get_current_span


class ClassSafetyTestMixin:

    def class_safety(self, class_, no_op_class):
        with self.assertWarns(UserWarning):
            bounded_attributes = class_()

        self.assertIsInstance(bounded_attributes, no_op_class)


class TestAPISafety(TestCase, ClassSafetyTestMixin):
    def test_bounded_attributes(self):
        self.class_safety(BoundedAttributes, dict)
