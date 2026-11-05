# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The value an instrument hands to the SDK when it records something.

Every ``add``, ``record`` or asynchronous callback result is turned into one
``Measurement`` by the instrument, then passed to the measurement consumer,
the views and finally an aggregation. Nothing downstream mutates it: the
dataclass is frozen.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from logging import getLogger
from typing import TYPE_CHECKING

from opentelemetry.attributes import _clean_attribute_value
from opentelemetry.context import Context
from opentelemetry.util.types import Attributes

_logger = getLogger(__name__)

if TYPE_CHECKING:
    from opentelemetry.sdk.metrics._internal.instrument import _Instrument


@dataclass(frozen=True)
class Measurement:
    """
    Represents a data point reported via the metrics API to the SDK.

    Args:
        value: Measured value.
        time_unix_nano: The time the API call was made to record the
            Measurement, in nanoseconds since the Unix epoch.
        instrument: The instrument that produced this `Measurement`.
        context: The active Context of the Measurement at API call time.
            The exemplar machinery reads the current span out of it, so an
            exemplar only carries a trace id and a span id when this Context
            held a recording span.
        attributes: Measurement attributes. Mutating mutable attribute values
            (lists or dicts) outside of the Measurement object can lead to
            undefined and bad behavior. ``None`` means the measurement was
            recorded without attributes, which is also what a value of the
            wrong type is replaced with.
    """

    value: int | float
    time_unix_nano: int
    instrument: _Instrument
    context: Context
    attributes: Attributes = None

    def __post_init__(self) -> None:
        """Normalise ``attributes`` right after the dataclass is built.

        A mapping is copied and cleaned. An empty key is dropped. A key that
        is not a string is converted with ``str`` when its type carries a
        usable one, and dropped when it does not. Values that are not valid
        attribute values are cast to ``str`` or replaced with ``None``. Anything that is not a mapping
        and not ``None`` is discarded altogether, ``attributes`` becomes
        ``None`` and a warning is logged. The frozen dataclass is written
        through ``object.__setattr__``, so this is the only point at which the
        field changes.
        """
        if self.attributes is not None:
            if isinstance(self.attributes, Mapping):
                object.__setattr__(
                    self,
                    "attributes",
                    _clean_attribute_value(self.attributes, None),
                )
            else:
                _logger.warning(
                    "Invalid type '%s' for attributes. Expected a Mapping or None.",
                    type(self.attributes),
                )
                object.__setattr__(self, "attributes", None)
