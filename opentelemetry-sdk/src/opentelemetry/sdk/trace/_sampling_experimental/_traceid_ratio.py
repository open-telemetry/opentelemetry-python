# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The composable sampler that samples a fixed fraction of spans.

The fraction is turned into a threshold once, at construction, so sampling a
span costs one attribute lookup. Which spans end up sampled is decided by the
composite sampler comparing that threshold against the span's randomness
value, which is why two services configured with the same ratio sample the
same traces rather than independently chosen ones.

Private to the ``_sampling_experimental`` subpackage, with no compatibility
guarantee.
"""

from __future__ import annotations

from collections.abc import Sequence

from opentelemetry.context import Context
from opentelemetry.trace import Link, SpanKind, TraceState
from opentelemetry.util.types import Attributes

from ._composable import ComposableSampler, SamplingIntent
from ._trace_state import serialize_th
from ._util import INVALID_THRESHOLD, MAX_THRESHOLD, calculate_threshold


class ComposableTraceIDRatioBased(ComposableSampler):
    """Composable sampler reporting one threshold derived from a ratio.

    A ratio that rounds to ``MAX_THRESHOLD``, which includes ``0.0``, cannot
    sample anything. The constructor stores ``INVALID_THRESHOLD`` and marks it
    unreliable in that case, so the sampler behaves exactly like
    ``composable_always_off`` while still describing itself with the ratio it
    was given.

    The constructor does not validate ``ratio``. Building this class directly
    with a ratio outside ``0.0`` to ``1.0`` can produce a threshold that
    ``is_valid_threshold`` rejects, in which case the composite sampler drops
    every span and reports nothing. Go through
    ``composable_traceid_ratio_based`` to get the range check.

    Args:
        ratio: Fraction of spans to sample, from ``0.0`` to ``1.0``. It is
            read once, to compute the threshold and to fill in the
            description, and is not retained as an attribute.
    """

    _threshold: int
    _description: str

    def __init__(self, ratio: float):
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        threshold = calculate_threshold(ratio)
        if threshold == MAX_THRESHOLD:
            threshold_str = "max"
        else:
            threshold_str = serialize_th(threshold)
        if threshold != MAX_THRESHOLD:
            intent = SamplingIntent(threshold=threshold)
        else:
            intent = SamplingIntent(threshold=INVALID_THRESHOLD, threshold_reliable=False)
        self._intent = intent
        self._description = f"ComposableTraceIDRatioBased{{threshold={threshold_str}, ratio={ratio}}}"

    def sampling_intent(
        self,
        parent_ctx: Context | None,
        name: str,
        span_kind: SpanKind | None,
        attributes: Attributes,
        links: Sequence[Link] | None,
        trace_state: TraceState | None,
    ) -> SamplingIntent:
        """Return the intent computed at construction, for any span.

        Args:
            parent_ctx: Ignored.
            name: Ignored.
            span_kind: Ignored.
            attributes: Ignored.
            links: Ignored.
            trace_state: Ignored, so the parent's ``th`` has no effect here.
                Combine this sampler with ``composable_parent_threshold`` when
                the ratio should apply to root spans only.

        Returns:
            The same intent object on every call, holding the threshold for
            the configured ratio, or an invalid threshold when the ratio
            samples nothing.
        """
        return self._intent

    def get_description(self) -> str:
        """Describe the sampler.

        Returns:
            The string built in the constructor, of the form
            ``ComposableTraceIDRatioBased{threshold=..., ratio=...}``. The
            threshold appears as compressed hexadecimal, or as ``max`` when
            the ratio samples nothing.
        """
        return self._description


def composable_traceid_ratio_based(
    ratio: float,
) -> ComposableSampler:
    """Returns a composable sampler that samples each span with a fixed ratio.

    - Returns a SamplingIntent with threshold determined by the configured sampling ratio
    - Sets threshold_reliable to true
    - Does not add any attributes

    Note:
        If the ratio is 0, it will behave as an ComposableAlwaysOff sampler instead.

    Args:
        ratio: The sampling ratio to use (between 0.0 and 1.0).

    Returns:
        A new sampler holding the threshold for ``ratio``. Each call builds a
        fresh instance.

    Raises:
        ValueError: If ``ratio`` is outside the closed interval from ``0.0``
            to ``1.0``, or is a NaN, which fails both comparisons.
    """
    if not 0.0 <= ratio <= 1.0:
        raise ValueError("Sampling ratio must be between 0.0 and 1.0")

    return ComposableTraceIDRatioBased(ratio)
