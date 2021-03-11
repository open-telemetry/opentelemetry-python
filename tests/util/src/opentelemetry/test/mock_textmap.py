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

from typing import Dict, Optional

from opentelemetry.context import Context, get_current
from opentelemetry.propagators.textmap import TextMapPropagator
from opentelemetry.trace import (
    INVALID_SPAN,
    NonRecordingSpan,
    SpanContext,
    get_current_span,
    set_span_in_context,
)


class NOOPTextMapPropagator(TextMapPropagator):
    """A propagator that does not extract nor inject.

    This class is useful for catching edge cases assuming
    a SpanContext will always be present.
    """

    def extract(
        self, carrier: Dict[str, str], context: Optional[Context] = None,
    ) -> Context:
        return get_current()

    def inject(
        self, carrier: Dict[str, str], context: Optional[Context] = None,
    ) -> None:
        return None

    @property
    def fields(self):
        return set()


class MockTextMapPropagator(TextMapPropagator):
    """Mock propagator for testing purposes."""

    trace_id_key = "mock-traceid"
    span_id_key = "mock-spanid"

    def extract(
        self, carrier: Dict[str, str], context: Optional[Context] = None,
    ) -> Context:
        trace_id = carrier.get(self.trace_id_key)
        span_id = carrier.get(self.span_id_key)

        if trace_id is None or span_id is None:
            return set_span_in_context(INVALID_SPAN)

        return set_span_in_context(
            NonRecordingSpan(
                SpanContext(
                    trace_id=trace_id, span_id=span_id, is_remote=True,
                )
            )
        )

    def inject(
        self, carrier: Dict[str, str], context: Optional[Context] = None,
    ) -> None:
        span = get_current_span(context)
        carrier[self.trace_id_key] = str(span.get_span_context().trace_id)
        carrier[self.span_id_key] = str(span.get_span_context().span_id)

    @property
    def fields(self):
        return {self.trace_id_key, self.span_id_key}
