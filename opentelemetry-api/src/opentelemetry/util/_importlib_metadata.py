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


@cache
def _all_entry_points_cached() -> EntryPoints:
    return EntryPoints(
        ep for dist in distributions() for ep in dist.entry_points
    )


def entry_points(**params) -> EntryPoints:
    if not params:
        return _all_entry_points_cached()
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
