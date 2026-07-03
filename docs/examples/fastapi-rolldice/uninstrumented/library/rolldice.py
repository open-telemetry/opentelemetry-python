# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Dice-rolling logic (uninstrumented).

This is the plain version of the rolldice library without any OpenTelemetry
instrumentation.  Compare with the instrumented version in the parent
directory to see what OTel adds.
"""

import logging
import random

logger = logging.getLogger(__name__)


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
    if rolls <= 0:
        raise ValueError(f"rolls must be a positive integer, got {rolls}")

    results = [_do_roll() for _ in range(rolls)]

    player_label = player or "anonymous player"
    logger.debug("%s rolled %s → %s", player_label, rolls, results)

    return results


def _do_roll() -> int:
    """Roll a single six-sided die and return the result."""
    return random.randint(1, 6)
