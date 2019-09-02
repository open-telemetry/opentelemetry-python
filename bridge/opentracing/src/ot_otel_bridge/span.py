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


from basictracer.span import BasicSpan

from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import Span as OtelSpan


class BridgeSpan(BasicSpan):
    def __init__(
        self,
        tracer,
        operation_name=None,
        context=None,
        parent_id=None,
        tags=None,
        start_time=None,
        otel_parent=None,
    ):
        super(BridgeSpan, self).__init__(
            tracer, operation_name, context, parent_id, tags, start_time
        )

        otel_context = trace_api.SpanContext(context.trace_id, context.span_id)
        if otel_parent is None:
            otel_parent = trace_api.SpanContext(context.trace_id, parent_id)
        otel_tags = tags

        self.otel_span = OtelSpan(
            name=operation_name,
            context=otel_context,
            parent=otel_parent,
            attributes=otel_tags,
        )

    def set_operation_name(self, operation_name):
        super(BridgeSpan, self).set_operation_name(operation_name)
        self.otel_span.update_name(operation_name)

    def set_tag(self, key, value):
        super(BridgeSpan, self).set_tag(key, value)
        self.otel_span.set_attribute(key, value)
