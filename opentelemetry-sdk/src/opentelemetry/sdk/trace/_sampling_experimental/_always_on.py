# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The composable sampler that samples every span.

Both the intent and the sampler are built once at import time and shared, so
calling the factory repeatedly costs nothing.

Private to the ``_sampling_experimental`` subpackage, with no compatibility
guarantee.
"""

from __future__ import annotations

from collections.abc import Sequence

from opentelemetry.context import Context
from opentelemetry.trace import Link, SpanKind, TraceState
from opentelemetry.util.types import Attributes

from ._composable import ComposableSampler, SamplingIntent
from ._util import MIN_THRESHOLD

_intent = SamplingIntent(threshold=MIN_THRESHOLD)


class _ComposableAlwaysOnSampler(ComposableSampler):
    """Composable sampler whose threshold admits every randomness value.

    It takes no construction arguments and keeps no state. Use the
    ``_always_on`` instance in this module rather than building another.
    """

    def sampling_intent(
        self,
        parent_ctx: Context | None,
        name: str,
        span_kind: SpanKind | None,
        attributes: Attributes,
        links: Sequence[Link] | None,
        trace_state: TraceState | None = None,
    ) -> SamplingIntent:
        """Return the fixed intent, whatever the span looks like.

        Args:
            parent_ctx: Ignored.
            name: Ignored.
            span_kind: Ignored.
            attributes: Ignored.
            links: Ignored.
            trace_state: Ignored. In particular the parent's ``th`` is not
                read, so this sampler overrides an upstream decision to drop.

        Returns:
            The shared intent holding ``MIN_THRESHOLD`` and a reliable
            threshold, which makes the composite sampler sample the span and
            write ``th:0`` into the outgoing ``ot`` entry.
        """
        return _intent

    def get_description(self) -> str:
        """Describe the sampler.

        Returns:
            The constant ``"ComposableAlwaysOn"``.
        """
        return "ComposableAlwaysOn"


_always_on = _ComposableAlwaysOnSampler()


def composable_always_on() -> ComposableSampler:
    """Returns a composable sampler that samples all spans.

    - Always returns a SamplingIntent with threshold set to sample all spans (threshold = 0)
    - Sets threshold_reliable to true
    - Does not add any attributes

    Returns:
        A shared, stateless sampler. Every call hands back the same instance.
    """
    return _always_on
