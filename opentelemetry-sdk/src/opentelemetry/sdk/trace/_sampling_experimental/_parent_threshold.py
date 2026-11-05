# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The composable sampler that inherits the parent span's threshold.

Once a root span has been sampled at some probability, every descendant reuses
the same threshold, and since every span of a trace is compared against the
same randomness value, they all reach the same decision. A span with no parent
has nothing to inherit, so it is handed to a separate root sampler chosen at
construction time.

Private to the ``_sampling_experimental`` subpackage, with no compatibility
guarantee.
"""

from __future__ import annotations

from collections.abc import Sequence

from opentelemetry.context import Context
from opentelemetry.trace import Link, SpanKind, TraceState, get_current_span
from opentelemetry.util.types import Attributes

from ._composable import ComposableSampler, SamplingIntent
from ._trace_state import OtelTraceState
from ._util import (
    INVALID_THRESHOLD,
    MIN_THRESHOLD,
    is_valid_threshold,
)


class _ComposableParentThreshold(ComposableSampler):
    """Composable sampler that reuses the threshold found on the parent.

    The description string is built once in the constructor, which means the
    root sampler's description is captured at that moment and a root sampler
    that later changes how it describes itself will not be reflected.

    Args:
        root_sampler: Sampler consulted for a span whose parent span context
            is not valid, which is what makes the span a root. Its
            description is embedded in this sampler's description.
    """

    def __init__(self, root_sampler: ComposableSampler):
        """Build the instance.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._root_sampler = root_sampler
        self._description = f"ComposableParentThreshold{{root={root_sampler.get_description()}}}"

    def sampling_intent(
        self,
        parent_ctx: Context | None,
        name: str,
        span_kind: SpanKind | None,
        attributes: Attributes,
        links: Sequence[Link] | None,
        trace_state: TraceState | None = None,
    ) -> SamplingIntent:
        """Derive the intent from the parent span, or from the root sampler.

        Three cases, in the order they are tried. A span whose parent span
        context is not valid is a root, and every argument is forwarded to the
        root sampler. Otherwise, if the parent's ``ot`` entry carries a usable
        ``th``, that threshold is reused and marked reliable. Otherwise only
        the sampled flag of the parent's trace flags is left to go on, which
        gives ``MIN_THRESHOLD`` when it is set and ``INVALID_THRESHOLD`` when
        it is not, marked unreliable either way because a flag says nothing
        about the probability behind it.

        Args:
            parent_ctx: Context holding the parent span, or ``None`` to mean
                the current context.
            name: The name the span will be created with. Used only when
                forwarding to the root sampler.
            span_kind: The kind the span will be created with, or ``None``.
                Used only when forwarding to the root sampler.
            attributes: The attributes known at creation time, or ``None``.
                Used only when forwarding to the root sampler.
            links: The links the span will be created with, or ``None``. Used
                only when forwarding to the root sampler.
            trace_state: The trace state inherited from the parent, or
                ``None``. The ``ot`` entry is read from here. ``None`` on a
                non-root span falls through to the trace flags.

        Returns:
            The root sampler's intent for a root span, otherwise an intent
            built here. Attributes are never added and the trace state is
            never updated by this sampler.
        """
        parent_span = get_current_span(parent_ctx)
        parent_span_ctx = parent_span.get_span_context()
        is_root = not parent_span_ctx.is_valid
        if is_root:
            return self._root_sampler.sampling_intent(parent_ctx, name, span_kind, attributes, links, trace_state)

        ot_trace_state = OtelTraceState.parse(trace_state)

        if is_valid_threshold(ot_trace_state.threshold):
            return SamplingIntent(
                threshold=ot_trace_state.threshold,
                threshold_reliable=True,
            )

        threshold = MIN_THRESHOLD if parent_span_ctx.trace_flags.sampled else INVALID_THRESHOLD
        return SamplingIntent(threshold=threshold, threshold_reliable=False)

    def get_description(self) -> str:
        """Describe the sampler.

        Returns:
            The string built in the constructor, of the form
            ``ComposableParentThreshold{root=...}`` with the root sampler's
            description inside the braces.
        """
        return self._description


def composable_parent_threshold(
    root_sampler: ComposableSampler,
) -> ComposableSampler:
    """Returns a consistent sampler that respects the sampling decision of
    the parent span or falls-back to the given sampler if it is a root span.

    - For spans without a parent context, delegate to the root sampler
    - For spans with a parent context, returns a SamplingIntent that propagates the parent's sampling decision
    - Returns the parent's threshold if available; otherwise, if the parent's sampled flag is set,
    returns threshold=0; otherwise, if the parent's sampled flag is not set, no threshold is returned.
    - Sets threshold_reliable to match the parent’s reliability, which is true if the parent had a threshold.
    - Does not add any attributes

    Args:
        root_sampler: The root sampler to use for spans without a parent context.

    Returns:
        A new sampler wrapping ``root_sampler``. Each call builds a fresh
        instance, since the description depends on the argument.
    """
    return _ComposableParentThreshold(root_sampler)
