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

from opentelemetry.distributedcontext import DistributedContext
from opentelemetry.trace import SpanContext


class UnifiedContext:
    """A unified context object that contains all context relevant to
    telemetry.

    The UnifiedContext is a single object that composes all contexts that
    are needed by the various forms of telemetry. It is intended to be an
    object that can be passed as the argument to any component that needs
    to read or modify content values (such as propagators). By unifying
    all context in a composed data structure, it expands the flexibility
    of the APIs that modify it.

    As it is designed to carry context specific to all telemetry use
    cases, it's schema is explicit. Note that this is not intended to
    be an object that acts as a singleton that returns different results
    based on the thread or coroutine of execution. For that, see `Context`.


    Args:
        distributed: The DistributedContext for this instance.
        span: The SpanContext for this instance.
    """
    __slots__ = ["distributed", "span"]

    def __init__(self, distributed: DistributedContext, span: SpanContext):
        self.distributed = distributed
        self.span = span

    @staticmethod
    def create(span: SpanContext) -> "UnifiedContext":
        """Create an unpopulated UnifiedContext object.

        Example:

            from opentelemetry.trace import tracer
            span = tracer.create_span("")
            context = UnifiedContext.create(span)


        Args:
            parent_span: the parent SpanContext that will be the
                parent of the span in the UnifiedContext.
        """
        return UnifiedContext(DistributedContext(), span)

    def __repr__(self) -> str:
        return "{}(distributed={}, span={})".format(
            type(self).__name__, repr(self.distributed), repr(self.span))
