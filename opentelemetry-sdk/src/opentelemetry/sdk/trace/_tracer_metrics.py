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

        sampling_results = {
            Decision.RECORD_AND_SAMPLE: OtelSpanSamplingResultValues.RECORD_AND_SAMPLE.value,
            Decision.RECORD_ONLY: OtelSpanSamplingResultValues.RECORD_ONLY.value,
            Decision.DROP: OtelSpanSamplingResultValues.DROP.value,
        }
        self._started_span_attrs = {
            None: {
                decision: {
                    OTEL_SPAN_PARENT_ORIGIN: "none",
                    OTEL_SPAN_SAMPLING_RESULT: sampling_result,
                }
                for decision, sampling_result in sampling_results.items()
            },
            False: {
                decision: {
                    OTEL_SPAN_PARENT_ORIGIN: "local",
                    OTEL_SPAN_SAMPLING_RESULT: sampling_result,
                }
                for decision, sampling_result in sampling_results.items()
            },
            True: {
                decision: {
                    OTEL_SPAN_PARENT_ORIGIN: "remote",
                    OTEL_SPAN_SAMPLING_RESULT: sampling_result,
                }
                for decision, sampling_result in sampling_results.items()
            },
        }
        self._live_span_attrs = {
            decision: {
                OTEL_SPAN_SAMPLING_RESULT: sampling_result,
            }
            for decision, sampling_result in sampling_results.items()
            if decision.is_recording()
        }
        self._record_end_metrics = {
            decision: self._new_end_span(live_span_attrs)
            for decision, live_span_attrs in self._live_span_attrs.items()
        }

    def _new_end_span(self, live_span_attrs: dict[str, str]) -> Callable[[], None]:
        def end_span() -> None:
            self._live_spans.add(-1, live_span_attrs)

        return end_span

    def start_span(
        self,
        parent_span_context: SpanContext | None,
        sampling_decision: Decision,
    ) -> Callable[[], None]:
        parent_origin_key = (
            None if parent_span_context is None else parent_span_context.is_remote
        )
        self._started_spans.add(
            1,
            self._started_span_attrs[parent_origin_key][sampling_decision],
        )

        live_span_attrs = self._live_span_attrs.get(sampling_decision)
        if live_span_attrs is None:
            return noop

        self._live_spans.add(1, live_span_attrs)
        return self._record_end_metrics[sampling_decision]


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
