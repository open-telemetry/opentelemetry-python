# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

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

    Attributes:
        value: Measured value
        time_unix_nano: The time the API call was made to record the Measurement
        instrument: The instrument that produced this `Measurement`.
        context: The active Context of the Measurement at API call time.
        attributes: Measurement attributes. Mutating mutable attribute values (lists or dicts)
        outside of the Measurement object can lead to undefined and bad behavior.
    """

    value: int | float
    time_unix_nano: int
    instrument: _Instrument
    context: Context
    attributes: Attributes = None

    def __post_init__(self) -> None:
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
