# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from functools import cache

# FIXME: Use importlib.metadata (not importlib_metadata)
# when support for 3.11 is dropped if the rest of
# the supported versions at that time have the same API.
from importlib_metadata import (  # type: ignore
    Distribution,
    EntryPoint,
    EntryPoints,
    PackageNotFoundError,
    distributions,
    requires,
    version,
)
from importlib_metadata import (
    entry_points as original_entry_points,
)


@cache
def _original_entry_points_cached():
    return original_entry_points()


def entry_points(**params) -> EntryPoints:
    """Replacement for importlib_metadata.entry_points that caches getting all the entry points.

    That part can be very slow, and OTel uses this function many times."""
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
