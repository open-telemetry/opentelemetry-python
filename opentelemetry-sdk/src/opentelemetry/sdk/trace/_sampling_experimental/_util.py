# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Threshold and randomness arithmetic for probability sampling.

A sampling probability is encoded as a 56-bit rejection threshold. A span is
sampled when its 56-bit randomness value is greater than or equal to the
threshold, so ``MIN_THRESHOLD`` (zero) samples everything, and
``MAX_THRESHOLD`` (two raised to the power of 56) samples nothing because no
randomness value can reach it. ``MAX_RANDOM_VALUE`` is one less than
``MAX_THRESHOLD``.

``INVALID_THRESHOLD`` and ``INVALID_RANDOM_VALUE`` are both ``-1``. They mark
the absence of a value rather than an encodable one, and the two validity
checks below reject them.

Private to the ``_sampling_experimental`` subpackage, with no compatibility
guarantee.
"""

RANDOM_VALUE_BITS = 56
MAX_THRESHOLD = 1 << RANDOM_VALUE_BITS  # 0% sampling
MIN_THRESHOLD = 0  # 100% sampling
MAX_RANDOM_VALUE = MAX_THRESHOLD - 1
INVALID_THRESHOLD = -1
INVALID_RANDOM_VALUE = -1

_probability_threshold_scale = float.fromhex("0x1p56")


def calculate_threshold(sampling_probability: float) -> int:
    """Convert a sampling probability into a 56-bit rejection threshold.

    The probability is scaled by two raised to the power of 56, rounded to the
    nearest integer and subtracted from ``MAX_THRESHOLD``. Probability ``1.0``
    therefore maps to ``MIN_THRESHOLD`` and probability ``0.0`` maps to
    ``MAX_THRESHOLD``. Rounding is what makes a probability too small to move
    the scaled value away from zero collapse onto ``MAX_THRESHOLD``, which
    samples nothing.

    The argument is not range checked here. A probability outside ``0.0`` to
    ``1.0`` yields a threshold that ``is_valid_threshold`` rejects.

    Args:
        sampling_probability: Fraction of spans to sample, expected in the
            closed interval from ``0.0`` to ``1.0``.

    Returns:
        The threshold that encodes that probability.
    """
    return MAX_THRESHOLD - round(sampling_probability * _probability_threshold_scale)


def is_valid_threshold(threshold: int) -> bool:
    """Report whether an integer can be used as a sampling threshold.

    The range is inclusive at both ends, so ``MAX_THRESHOLD`` counts as valid
    even though a span carrying it is never sampled. ``INVALID_THRESHOLD`` and
    anything else below ``MIN_THRESHOLD`` is rejected.

    Args:
        threshold: The integer to check.

    Returns:
        ``True`` when the integer lies between ``MIN_THRESHOLD`` and
        ``MAX_THRESHOLD`` inclusive.
    """
    return MIN_THRESHOLD <= threshold <= MAX_THRESHOLD


def is_valid_random_value(random_value: int) -> bool:
    """Report whether an integer can be used as a 56-bit randomness value.

    The upper bound is ``MAX_RANDOM_VALUE``, one less than ``MAX_THRESHOLD``.
    ``INVALID_RANDOM_VALUE`` is rejected, which is how an ``ot`` trace state
    entry with no usable ``rv`` field is detected.

    Args:
        random_value: The integer to check.

    Returns:
        ``True`` when the integer is non-negative and fits in 56 bits.
    """
    return 0 <= random_value <= MAX_RANDOM_VALUE
