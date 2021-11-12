# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from dataclasses import dataclass
from typing import Callable, Optional, Union

from opentelemetry.sdk._metrics._internal.instrument_descriptor import (
    InstrumentDescriptor,
)
from opentelemetry.util.types import Attributes

SendMeasurementT = Callable[["Measurement"], None]
ValueT = Union[int, float]


@dataclass(frozen=True)
class Measurement:
    """A measurement as recorded by an instrument"""

    instrument_descriptor: InstrumentDescriptor
    value: Union[int, float]
    attributes: Attributes
