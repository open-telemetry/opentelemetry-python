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

from opentelemetry.context import Context, get_current, get_value
from opentelemetry.trace import INVALID_SPAN_CONTEXT, Span, SpanContext

_SPAN_CONTEXT_KEY = "extracted-span-context"
_SPAN_KEY = "current-span"


def span_context_from_context(
    context: Optional[Context] = None,
) -> SpanContext:
    span = span_from_context(context=context)
    if span is not None:
        return span.get_context()
    sc = get_value(_SPAN_CONTEXT_KEY, context=context)
    if sc is not None:
        return sc

    return INVALID_SPAN_CONTEXT


def with_span_context(
    span_context: SpanContext, context: Optional[Context] = None
) -> None:
    if context is not None:
        context.set_value(_SPAN_CONTEXT_KEY, span_context)
    return get_current().set_value(_SPAN_CONTEXT_KEY, span_context)


def _get_span_key(name: Optional[str] = None) -> str:
    key = _SPAN_KEY
    if name is not None:
        key = "{}-{}".format(key, name)
    return key


def span_from_context(
    context: Optional[Context] = None, name: Optional[str] = None
) -> Span:
    key = _get_span_key(name)
    return get_value(key, context)


def with_span(
    span: Span, context: Optional[Context] = None, name: Optional[str] = None
) -> None:
    key = _get_span_key(name)
    if context is not None:
        return context.set_value(key, span)
    return get_current().set_value(key, span)
