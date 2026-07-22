# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Dice-rolling logic for the rolldice reference application.

──────────────────────────────────────────────────────────────────────────────
IMPORTANT: This module imports ONLY from ``opentelemetry`` (the API package).
It does NOT import from ``opentelemetry.sdk`` or any SDK subpackage.

This is intentional and reflects the recommended OTel library design:

  • Library code should depend only on the *API* so it can be used in
    applications that choose any SDK implementation (or no SDK at all).

  • The *SDK* — which actually records spans, collects metrics, and exports
    telemetry — is configured once by the *application* (in ``app/telemetry.py``).

  • When the application installs an SDK via ``set_tracer_provider()`` /
    ``set_meter_provider()``, the API calls below automatically delegate to it.
    Without an installed SDK the API calls are no-ops, so this library is safe
    to use in any context.
──────────────────────────────────────────────────────────────────────────────
"""

import logging
import random

# opentelemetry.trace and opentelemetry.metrics are the *API* namespaces.
# They expose get_tracer() and get_meter(), which return a Tracer/Meter bound
# to whatever provider the application has installed (or a no-op if none).
from opentelemetry import metrics, trace

# Observation is used to yield values from ObservableGauge callbacks.
from opentelemetry.metrics import Observation

logger = logging.getLogger(__name__)

# ── Tracer ───────────────────────────────────────────────────────────────────
# get_tracer() returns a Tracer scoped to this instrumentation library.
# The name (__name__ = "library.rolldice") becomes the instrumentation scope
# name visible in trace backends; it is not the span name.
_tracer = trace.get_tracer(__name__)

# ── Meter and instruments ────────────────────────────────────────────────────
# get_meter() returns a Meter scoped to this library.  Metric instruments
# (Counter, Histogram, ObservableGauge) are created once at module load time;
# creating them repeatedly would produce duplicate registrations.
_meter = metrics.get_meter(__name__)

# Counter: monotonically increasing.  Use it for things that are counted and
# never decrease, like the total number of dice rolls requested.
_calls_counter = _meter.create_counter(
    "rolldice.calls",
    description="Total number of roll_dice() calls",
)

# Histogram: records a distribution of values.  Use it to understand the
# spread of measurements — here, which dice faces (1-6) are landed on most.
_outcome_histogram = _meter.create_histogram(
    "rolldice.outcome",
    description="Distribution of individual dice outcomes (1–6)",
)

# ObservableGauge: reports the current value of something at collection time
# via a callback.  Prefer it over an UpDownCounter when you care about the
# instantaneous value, not the cumulative change.  Here it tracks the most
# recent ``rolls`` argument so operators can see the last workload size.
_last_rolls_value: int = 0


def _observe_last_rolls(options: metrics.CallbackOptions):
    """Callback invoked by the SDK at each metric collection interval."""
    yield Observation(_last_rolls_value)


_last_rolls_gauge = _meter.create_observable_gauge(
    "rolldice.last_rolls",
    callbacks=[_observe_last_rolls],
    description="Most recent value of the rolls parameter",
)


def roll_dice(rolls: int, player: str | None = None) -> list[int]:
    """Roll a six-sided die ``rolls`` times and return the results.

    Args:
        rolls: Number of dice to roll.  Must be a positive integer.
        player: Optional display name for the player (used in log output).

    Returns:
        A list of ``rolls`` integers, each in the range [1, 6].

    Raises:
        ValueError: If ``rolls`` is not a positive integer.
    """
    # with_span() is a context manager that:
    #   1. Creates a new span named "roll_dice" as a child of the current
    #      active span (the HTTP request span created by FastAPIInstrumentor).
    #   2. Sets it as the active span for the duration of the block.
    #   3. Ends the span (and records any exception) when the block exits.
    with _tracer.start_as_current_span("roll_dice") as span:
        # Semantic convention attributes describe the code location that
        # created the span.  code.function and code.filepath are part of the
        # "code" namespace in the OTel semantic conventions.
        span.set_attribute("code.function", "roll_dice")
        span.set_attribute("code.filepath", __file__)

        # Application-specific attribute: how many rolls were requested.
        # Recording it on the span lets you filter traces by workload size.
        span.set_attribute("rolls", rolls)

        if rolls <= 0:
            # record_exception() attaches the exception details as a span event
            # with the standard "exception.*" attributes, then we re-raise so
            # the caller (the HTTP handler) can return a 500 response.
            exc = ValueError(f"rolls must be a positive integer, got {rolls}")
            span.record_exception(exc)
            raise exc

        results = [_do_roll() for _ in range(rolls)]

        # Update the module-level variable observed by the gauge callback.
        global _last_rolls_value
        _last_rolls_value = rolls

        # Counter: increment by 1 for this call, regardless of roll count.
        _calls_counter.add(1)

        # Histogram: record each individual outcome so the distribution of
        # dice faces is captured.
        for value in results:
            _outcome_histogram.record(value)

        player_label = player or "anonymous player"
        logger.debug("%s rolled %s → %s", player_label, rolls, results)

        return results


def _do_roll() -> int:
    """Roll a single six-sided die and return the result.

    This inner function has its own span so the trace shows both the
    aggregate ``roll_dice`` operation and each individual roll, making
    it easy to see exactly how long each random number generation took.
    """
    with _tracer.start_as_current_span("_do_roll") as span:
        value = random.randint(1, 6)
        # Record the generated value on the span so you can inspect individual
        # roll results in a trace backend without needing to look at logs.
        span.set_attribute("roll.value", value)
        return value
