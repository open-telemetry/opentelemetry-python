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

from opentelemetry.context import BaseRuntimeContext, Context
from opentelemetry.trace import SpanContext
from opentelemetry.trace.propagation import ContextKeys


def from_context(ctx: Optional[BaseRuntimeContext] = None) -> SpanContext:
    if ctx is None:
        ctx = Context.current()
    return Context.value(ctx, ContextKeys.span_context_key())


def with_span_context(
    ctx: BaseRuntimeContext, span_context: SpanContext
) -> BaseRuntimeContext:
    return Context.set_value(
        ctx, ContextKeys.span_context_key(), span_context,
    )

