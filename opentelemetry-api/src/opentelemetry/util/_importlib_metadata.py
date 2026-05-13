# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

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
def _all_entry_points_cached() -> EntryPoints:
    return _as_entry_points(original_entry_points())


def entry_points(**params) -> EntryPoints:
    return _all_entry_points_cached().select(**params)


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
