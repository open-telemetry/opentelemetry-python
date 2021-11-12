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
from enum import Enum
from typing import Optional


class InstrumentType(Enum):
    COUNTER = "COUNTER"
    HISTOGRAM = "HISTOGRAM"
    OBSERVABLE_COUNTER = "OBSERVABLE_COUNTER"
    OBSERVABLE_GAUGE = "OBSERVABLE_GAUGE"
    OBSERVABLE_UP_DOWN_COUNTER = "OBSERVABLE_UP_DOWN_COUNTER"
    UP_DOWN_COUNTER = "UP_DOWN_COUNTER"


@dataclass(frozen=True)
class ViewSelector:
    instrument_name: Optional[str] = None
    instrument_type: Optional[InstrumentType] = None
    meter_name: Optional[str] = None
    meter_schema_url: Optional[str] = None
    meter_version: Optional[str] = None


@dataclass(frozen=True)
class View:
    selector: ViewSelector
    name: Optional[str] = None
