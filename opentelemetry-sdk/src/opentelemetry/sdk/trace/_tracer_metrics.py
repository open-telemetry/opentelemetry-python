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

from __future__ import annotations

from collections.abc import Callable

from opentelemetry import metrics as metrics_api
from opentelemetry.sdk.trace.sampling import Decision
from opentelemetry.trace.span import SpanContext


class TracerMetrics:
    def __init__(self, meter_provider: metrics_api.MeterProvider) -> None:
        meter = meter_provider.get_meter("opentelemetry-sdk")

        self._started_spans = meter.create_counter(
            "otel.sdk.span.started", "{span}", "The number of created spans"
        )
        self._live_spans = meter.create_up_down_counter(
            "otel.sdk.span.live",
            "{span}",
            "The number of currently live spans",
        )

    def start_span(
        self,
        parent_span_context: SpanContext | None,
        sampling_decision: Decision,
    ) -> Callable[[], None]:
        self._started_spans.add(
            1,
            {
                "otel.span.parent.origin": parent_origin(parent_span_context),
                "otel.span.sampling_result": sampling_decision.name,
            },
        )

        if sampling_decision == Decision.DROP:
            return noop

        live_span_attrs = {
            "otel.span.sampling_result": sampling_decision.name,
        }
        self._live_spans.add(1, live_span_attrs)

        def end_span() -> None:
            self._live_spans.add(-1, live_span_attrs)

        return end_span


def noop() -> None:
    pass


def parent_origin(span_ctx: SpanContext | None) -> str:
    if span_ctx is None:
        return "none"
    if span_ctx.is_remote:
        return "remote"
    return "local"
