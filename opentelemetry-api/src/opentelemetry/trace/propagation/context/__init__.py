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
from typing import Optional

from opentelemetry.context import Context
from opentelemetry.trace import Span, SpanContext, INVALID_SPAN_CONTEXT
from opentelemetry.trace.propagation import ContextKeys


def span_context_from_context(ctx: Optional[Context] = None) -> SpanContext:
    span = span_from_context(context=ctx)
    if span:
        return span.get_context()
    sc = Context.value(ContextKeys.span_context_key(), context=ctx)  # type: ignore
    if sc:
        return sc

    return INVALID_SPAN_CONTEXT


def with_span_context(span_context: SpanContext) -> Context:
    return Context.set_value(ContextKeys.span_context_key(), span_context)


def span_from_context(context: Optional[Context] = None) -> Span:
    return Context.value(ContextKeys.span_key(), context=context)  # type: ignore


def with_span(span: Span) -> Context:
    return Context.set_value(ContextKeys.span_key(), span)
