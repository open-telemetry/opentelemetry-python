# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Experimental consistent probability samplers.

This subpackage is private and experimental. The leading underscore in its
name is the warning: names exported here may change or disappear in any
release, including a patch release, and nothing in it is covered by the
compatibility guarantees that apply to the rest of
``opentelemetry.sdk.trace``.

It implements the sampling scheme described by
https://opentelemetry.io/docs/specs/otel/trace/tracestate-probability-sampling/
in which a sampling probability is encoded as a 56-bit threshold carried in
the ``th`` field of the ``ot`` trace state entry, and the decision is made by
comparing that threshold against a 56-bit randomness value, taken from the
``rv`` field of the same entry or from the low 56 bits of the trace id. Every
service in a trace that runs the same scheme therefore reaches the same
decision, and a backend can recover an unbiased span count from the threshold
each sampled span carries.

Samplers here implement ``ComposableSampler``, which reports a threshold
rather than a decision. That makes them nestable: ``composable_rule_based``
chooses among them by predicate and ``composable_parent_threshold`` falls back
to one for root spans. Wrap the outermost one in ``composite_sampler`` to get
an ordinary SDK ``Sampler`` that a tracer provider accepts.
"""

__all__ = [
    "ComposableSampler",
    "SamplingIntent",
    "composable_always_off",
    "composable_always_on",
    "composable_parent_threshold",
    "composable_rule_based",
    "composable_traceid_ratio_based",
    "composite_sampler",
]


from ._always_off import composable_always_off
from ._always_on import composable_always_on
from ._composable import ComposableSampler, SamplingIntent
from ._parent_threshold import composable_parent_threshold
from ._rule_based import composable_rule_based
from ._sampler import composite_sampler
from ._traceid_ratio import composable_traceid_ratio_based
