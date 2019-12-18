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
import typing

from opentelemetry.context.propagation import (
    Getter,
    HTTPExtractor,
)

import opentelemetry.trace as trace
from opentelemetry.trace.propagation.context import Context, with_span_context

_T = typing.TypeVar("_T")


class WSGIExtractor(HTTPExtractor):
    """ TODO """

    @classmethod
    def extract(
        cls,
        carrier,
        context: typing.Optional[Context] = None,
        get_from_carrier: typing.Optional[Getter[_T]] = None,
    ):
        """ TODO """
        trace_id = get_from_carrier(carrier, "TRACE_ID")
        span_id = get_from_carrier(carrier, "SPAN_ID")
        options = get_from_carrier(carrier, "OPTIONS")
        if not trace_id or not span_id:
            return with_span_context(trace.INVALID_SPAN_CONTEXT)

        return with_span_context(
            trace.SpanContext(
                # trace an span ids are encoded in hex, so must be converted
                trace_id=int(trace_id, 16),
                span_id=int(span_id, 16),
                trace_options=trace.TraceOptions(options),
                trace_state=trace.TraceState(),
            ),
        )
