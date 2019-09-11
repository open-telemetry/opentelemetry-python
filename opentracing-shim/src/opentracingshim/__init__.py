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
    # def __init__(self, tracer, context):
    #     self._tracer = tracer
    #     self._context = context
    def __init__(self, span: OTelSpan):
        self._otel_span = span

    @property
    def otel_span(self):
        """Returns the OpenTelemetry span embedded in the SpanWrapper."""
        return self._otel_span

    @property
    def context(self):
        # return self._context
        pass

    @property
    def tracer(self):
        # return self._tracer
        pass

    def set_operation_name(self, operation_name):
        self._otel_span.update_name(operation_name)
        return self

    def finish(self, finish_time=None):
        pass

    def set_tag(self, key, value):
        return self

    def log_kv(self, key_values, timestamp=None):
        return self

    def set_baggage_item(self, key, value):
        return self

    def get_baggage_item(self, key):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        Span._on_error(self, exc_type, exc_val, exc_tb)
        self.finish()

    @staticmethod
    def _on_error(span, exc_type, exc_val, exc_tb):
        # if not span or not exc_val:
        #     return

        # span.set_tag(tags.ERROR, True)
        # span.log_kv({
        #     logs.EVENT: tags.ERROR,
        #     logs.MESSAGE: str(exc_val),
        #     logs.ERROR_OBJECT: exc_val,
        #     logs.ERROR_KIND: exc_type,
        #     logs.STACK: exc_tb,
        # })
        pass

    def log_event(self, event, payload=None):
        # """DEPRECATED"""
        # if payload is None:
        #     return self.log_kv({logs.EVENT: event})
        # else:
        #     return self.log_kv({logs.EVENT: event, 'payload': payload})
        pass

    def log(self, **kwargs):
        # """DEPRECATED"""
        # key_values = {}
        # if logs.EVENT in kwargs:
        #     key_values[logs.EVENT] = kwargs[logs.EVENT]
        # if 'payload' in kwargs:
        #     key_values['payload'] = kwargs['payload']
        # timestamp = None
        # if 'timestamp' in kwargs:
        #     timestamp = kwargs['timestamp']
        # return self.log_kv(key_values, timestamp)
        pass

class ScopeWrapper(OTScope):
    def __init__(self, manager, span):
        self._manager = manager
        self._span = span

    @property
    def span(self):
        return self._span

    @property
    def manager(self):
        return self._manager

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        SpanWrapper._on_error(self.span, exc_type, exc_val, exc_tb)
        self.close()

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
        # TODO: Activate the OTel span.
        # otel_span = self._otel_tracer.start_span(operation_name)
        otel_span = self._otel_tracer.create_span(operation_name)
        return ScopeWrapper(None, SpanWrapper(otel_span))

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
