# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""
Caching and compatibility wrapper for standard library ``importlib.metadata``.

This module caches ``entry_points()`` to avoid reloading entry points from disk on every call.
It also normalizes minor differences across python versions 3.10+. References to issues:

- https://github.com/open-telemetry/opentelemetry-python/pull/4735
- https://github.com/open-telemetry/opentelemetry-python/pull/5203
"""

import itertools
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
    """Normalize the result of ``importlib.metadata.entry_points()``.

    The standard library returns different types on different Python versions.
    This flattens whichever form it receives into a single
    :class:`importlib.metadata.EntryPoints` holding every entry point of every
    group.

    Args:
        eps: The value returned by ``importlib.metadata.entry_points()``. It is
            an :class:`~importlib.metadata.EntryPoints` on Python 3.12 and
            later, and a dict-like ``SelectableGroups`` on Python 3.10 and 3.11.

    Returns:
        Every entry point from ``eps``, collected into one
        :class:`~importlib.metadata.EntryPoints`.
    """
    # Python versions greater than 3.11 return EntryPoints.
    if isinstance(eps, EntryPoints):
        return eps
    # In Python 3.10 and 3.11 entry_points() returns
    # a dict-like SelectableGroups object.
    # Use dict.values() instead of eps.values() to avoid the DeprecationWarning
    # that SelectableGroups raises when calling .values().
    if isinstance(eps, dict):
        return EntryPoints(itertools.chain.from_iterable(dict.values(eps)))
    # This case should be unreachable, but is included as a fallback.
    return EntryPoints(ep for group in eps.groups for ep in eps.select(group=group))


@cache
def _original_entry_points_cached() -> EntryPoints:
    """Read every installed entry point and cache the result.

    Reading entry points touches the filesystem, so the result is cached for
    the lifetime of the process. A distribution installed after the first call
    is therefore not visible.

    :func:`functools.cache` holds no lock across the wrapped call, so threads
    that arrive before the first call returns each perform the read, and the
    last one to finish supplies the cached value.

    Returns:
        Every entry point installed in the current environment.
    """
    return _as_entry_points(original_entry_points())


def entry_points(**params) -> EntryPoints:
    """Select installed entry points, reading them from cache.

    This is a drop-in replacement for ``importlib.metadata.entry_points()``
    that behaves the same on every supported Python version and avoids
    re-reading the filesystem on each call.

    Args:
        **params: Selection criteria forwarded to
            :meth:`importlib.metadata.EntryPoints.select`, typically ``group``
            and ``name``. Passing none selects every entry point.

    Returns:
        The entry points matching ``params``, empty if none match.
    """
    return _original_entry_points_cached().select(**params)


__all__ = [
    "Distribution",
    "EntryPoint",
    "EntryPoints",
    "PackageNotFoundError",
    "distributions",
    "entry_points",
    "requires",
    "version",
]
