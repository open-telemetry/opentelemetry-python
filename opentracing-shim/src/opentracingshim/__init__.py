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

from opentelemetry.trace import Tracer as OTelTracer
from opentelemetry.trace import Span as OTelSpan
from opentracing import Scope as OTScope
from opentracing import Tracer as OTTracer
from opentracing import Span as OTSpan

def create_tracer(tracer: OTelTracer) -> OTTracer:
    return TracerWrapper(tracer)

class SpanWrapper(OTSpan):
    # def __init__(self, span: OTelSpan):
        # self._otel_span = span
    def __init__(self):
        pass

class ScopeWrapper(OTScope):
    def __init__(self):
        self._span = SpanWrapper()

    @property
    def span(self):
        return self._span

class TracerWrapper(OTTracer):
    def __init__(self, tracer: OTelTracer):
        self._otel_tracer = tracer
        # TODO: Finish implementation.

    @property
    def scope_manager(self):
        # return self._scope_manager
        # TODO: Implement.
        pass

    @property
    def active_span(self):
        # scope = self._scope_manager.active
        # return None if scope is None else scope.span
        # TODO: Implement.
        pass

    def start_active_span(self,
                          operation_name,
                          child_of=None,
                          references=None,
                          tags=None,
                          start_time=None,
                          ignore_active_span=False,
                          finish_on_close=True) -> ScopeWrapper:
        # TODO: Implement.
        return ScopeWrapper()

    def start_span(self,
                   operation_name=None,
                   child_of=None,
                   references=None,
                   tags=None,
                   start_time=None,
                   ignore_active_span=False):
        # return self._noop_span
        # TODO: Implement.
        pass

    def inject(self, span_context, format, carrier):
        # if format in Tracer._supported_formats:
        #     return
        # raise UnsupportedFormatException(format)
        # TODO: Implement.
        pass

    def extract(self, format, carrier):
        # if format in Tracer._supported_formats:
        #     return self._noop_span_context
        # raise UnsupportedFormatException(format)
        # TODO: Implement.
        pass
