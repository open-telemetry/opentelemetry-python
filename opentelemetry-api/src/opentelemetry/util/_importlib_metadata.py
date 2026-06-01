# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""
Caching and compatibility wrapper for standard library ``importlib.metadata``.

This module caches ``entry_points()`` to avoid reloading entry points from disk on every call.
It also normalizes minor differences across python versions 3.10+. References to issues:

- https://github.com/open-telemetry/opentelemetry-python/pull/4735
- https://github.com/open-telemetry/opentelemetry-python/pull/5203
- https://github.com/open-telemetry/opentelemetry-python/issues/5231
"""

import warnings
from functools import cache
from importlib.metadata import (
    Distribution,
    EntryPoint,
    EntryPoints,
    PackageNotFoundError,
    distributions,
    requires,
    version,
)
from importlib.metadata import entry_points as original_entry_points
from typing import Any


def _as_entry_points(eps: Any) -> EntryPoints:
    if isinstance(eps, EntryPoints):
        return eps
    # Handle Python 3.10 SelectableGroups (dict-like)
    return EntryPoints(ep for group_eps in eps.values() for ep in group_eps)


@cache
def _original_entry_points_cached() -> EntryPoints:
    # On Python 3.10 and 3.11, calling entry_points() without arguments returns
    # a SelectableGroups object. Its .values() method emits a DeprecationWarning
    # ("SelectableGroups dict interface is deprecated. Use select.") that cannot
    # be avoided while caching all entry points in a single upfront call.
    # The @cache decorator ensures this path runs only once per interpreter
    # session, so suppressing the warning here is both safe and targeted.
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=DeprecationWarning,
            message="SelectableGroups dict interface is deprecated",
        )
        return _as_entry_points(original_entry_points())


def entry_points(**params) -> EntryPoints:
    return _original_entry_points_cached().select(**params)


__all__ = [
    "entry_points",
    "version",
    "EntryPoint",
    "EntryPoints",
    "requires",
    "Distribution",
    "distributions",
    "PackageNotFoundError",
]
