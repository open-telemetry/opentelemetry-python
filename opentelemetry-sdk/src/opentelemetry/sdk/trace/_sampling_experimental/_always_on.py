# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from opentelemetry.context import Context
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.trace import Link, SpanKind, TraceState
from opentelemetry.util.types import Attributes

from ._composable import ComposableSampler, SamplingIntent
from ._util import MIN_THRESHOLD

_intent = SamplingIntent(threshold=MIN_THRESHOLD)


class _ComposableAlwaysOnSampler(ComposableSampler):
    def sampling_intent(
        self,
        parent_ctx: Context | None,
        name: str,
        span_kind: SpanKind | None,
        attributes: Attributes,
        links: Sequence[Link] | None,
        trace_state: TraceState | None = None,
        *,
        span_type: str | None = None,
        instrumentation_scope: InstrumentationScope | None = None,
        resource: Resource | None = None,
        **kwargs: Any,
    ) -> SamplingIntent:
        return _intent

    def get_description(self) -> str:
        return "ComposableAlwaysOn"


_always_on = _ComposableAlwaysOnSampler()


def composable_always_on() -> ComposableSampler:
    """Returns a composable sampler that samples all spans.

    - Always returns a SamplingIntent with threshold set to sample all spans (threshold = 0)
    - Sets threshold_reliable to true
    - Does not add any attributes
    """
    return _always_on
