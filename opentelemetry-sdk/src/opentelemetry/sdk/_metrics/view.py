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

from typing import Callable, Dict, List

from opentelemetry._metrics.instrument import Instrument
from opentelemetry.sdk._metrics.aggregation import Aggregation


class View:
    def __init__(
        self,
        instrument_type: Instrument = None,
        instrument_name: str = None,
        meter_name: str = None,
        meter_version: str = None,
        meter_schema_url: str = None,
        name: str = None,
        description: str = None,
        attribute_keys: Dict[str, str] = None,
        extra_dimensions: List[str] = None,
        aggregation: Aggregation = None,
        exemplar_reservoir: Callable = None,
    ):
        pass

    def _matches(self, instrument: Instrument) -> bool:
        pass
