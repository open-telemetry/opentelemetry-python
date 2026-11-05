# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The composable sampler that drops every span.

It reports no threshold at all, ``INVALID_THRESHOLD``, rather than the
``MAX_THRESHOLD`` that encodes a probability of zero. The composite sampler
then skips the randomness comparison altogether instead of performing one
whose outcome is already known.

Both the intent and the sampler are built once at import time and shared.

Private to the ``_sampling_experimental`` subpackage, with no compatibility
guarantee.
"""

from __future__ import annotations

from collections.abc import Sequence

from opentelemetry.context import Context
from opentelemetry.trace import Link, SpanKind, TraceState
from opentelemetry.util.types import Attributes

from ._composable import ComposableSampler, SamplingIntent
from ._util import INVALID_THRESHOLD

_intent = SamplingIntent(threshold=INVALID_THRESHOLD, threshold_reliable=False)


class _ComposableAlwaysOffSampler(ComposableSampler):
    """Composable sampler that reports no threshold for any span.

    It takes no construction arguments and keeps no state. Use the
    ``_always_off`` instance in this module rather than building another.
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
            trace_state: Ignored. The parent's ``th`` is not read, so a
                sampled parent does not keep the span alive.

        Returns:
            The shared intent holding ``INVALID_THRESHOLD`` and an unreliable
            threshold, which makes the composite sampler drop the span and
            leave ``th`` out of the ``ot`` entry it writes. A parent entry
            that held nothing but ``th`` is passed on unchanged instead,
            because the composite sampler only writes an entry that
            serializes to a non-empty string.
        """
        return _intent

    def get_description(self) -> str:
        """Describe the sampler.

        Returns:
            The constant ``"ComposableAlwaysOff"``.
        """
        return "ComposableAlwaysOff"


_always_off = _ComposableAlwaysOffSampler()


def composable_always_off() -> ComposableSampler:
    """Returns a composable sampler that does not sample any span.

    - Always returns a SamplingIntent with no threshold, indicating all spans should be dropped
    - Sets threshold_reliable to false
    - Does not add any attributes

    Returns:
        A shared, stateless sampler. Every call hands back the same instance.
    """
    return _always_off
