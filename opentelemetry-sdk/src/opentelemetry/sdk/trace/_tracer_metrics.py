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
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OTEL_SPAN_PARENT_ORIGIN,
    OTEL_SPAN_SAMPLING_RESULT,
    OtelSpanSamplingResultValues,
)
from opentelemetry.semconv._incubating.metrics.otel_metrics import (
    create_otel_sdk_span_live,
    create_otel_sdk_span_started,
)
from opentelemetry.trace.span import SpanContext


class TracerMetrics:
    def __init__(self, meter_provider: metrics_api.MeterProvider) -> None:
        meter = meter_provider.get_meter("opentelemetry-sdk")

        self._started_spans = create_otel_sdk_span_started(meter)
        self._live_spans = create_otel_sdk_span_live(meter)

    def start_span(
        self,
        parent_span_context: SpanContext | None,
        sampling_decision: Decision,
    ) -> Callable[[], None]:
        sampling_result_value = sampling_result(sampling_decision)
        self._started_spans.add(
            1,
            {
                OTEL_SPAN_PARENT_ORIGIN: parent_origin(parent_span_context),
                OTEL_SPAN_SAMPLING_RESULT: sampling_result_value,
            },
        )

        if not sampling_decision.is_recording():
            return noop

        live_span_attrs = {
            OTEL_SPAN_SAMPLING_RESULT: sampling_result_value,
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


def sampling_result(decision: Decision) -> str:
    if decision == Decision.RECORD_AND_SAMPLE:
        return OtelSpanSamplingResultValues.RECORD_AND_SAMPLE.value
    if decision == Decision.RECORD_ONLY:
        return OtelSpanSamplingResultValues.RECORD_ONLY.value
    return OtelSpanSamplingResultValues.DROP.value
