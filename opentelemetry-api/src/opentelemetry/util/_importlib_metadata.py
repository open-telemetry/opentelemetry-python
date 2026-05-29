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
    # On Python 3.10 and 3.11, entry_points() returns a SelectableGroups
    # object whose dict interface is deprecated and emits a DeprecationWarning
    # when iterated via .values().  The correct way to flatten the groups is
    # to call .select() without filters, which returns a flat EntryPoints list
    # without triggering the deprecation warning.
    # See: https://github.com/open-telemetry/opentelemetry-python/issues/5231
    if hasattr(eps, "select"):
        return eps.select()
    # Fallback for any other dict-like structure (should not be reached in
    # practice but kept for robustness).
    return EntryPoints(ep for group_eps in eps.values() for ep in group_eps)


@cache
def _original_entry_points_cached() -> EntryPoints:
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
