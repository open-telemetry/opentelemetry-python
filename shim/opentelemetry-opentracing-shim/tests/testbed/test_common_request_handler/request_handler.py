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

from opentracing.ext import tags

# pylint: disable=import-error
from ..utils import get_logger

logger = get_logger(__name__)


class RequestHandler:
    def __init__(self, tracer, context=None, ignore_active_span=True):
        self.tracer = tracer
        self.context = context
        self.ignore_active_span = ignore_active_span

    def before_request(self, request, request_context):
        logger.info("Before request %s", request)

        # If we should ignore the active Span, use any passed SpanContext
        # as the parent. Else, use the active one.
        if self.ignore_active_span:
            span = self.tracer.start_span(
                "send", child_of=self.context, ignore_active_span=True
            )
        else:
            span = self.tracer.start_span("send")

        span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_RPC_CLIENT)

        request_context["span"] = span

    def after_request(self, request, request_context):
        # pylint: disable=no-self-use
        logger.info("After request %s", request)

        span = request_context.get("span")
        if span is not None:
            span.finish()
