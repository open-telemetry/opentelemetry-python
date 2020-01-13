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
from opentelemetry.correlationcontext import CorrelationContext
from opentelemetry.correlationcontext.propagation import ContextKeys


def correlation_context_from_context(
    ctx: Optional[Context] = None,
) -> CorrelationContext:
    return Context.value(ContextKeys.span_context_key(), context=ctx)  # type: ignore


def with_correlation_context(
    correlation_context: CorrelationContext,
) -> Context:
    return Context.set_value(
        ContextKeys.span_context_key(), correlation_context
    )
