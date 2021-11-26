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

from typing import Callable, Dict, Iterable, List

from opentelemetry.sdk._metrics.aggregation import Aggregation
from opentelemetry.sdk._metrics.export import Metric
from opentelemetry.sdk._metrics.measurement import Measurement
from opentelemetry.sdk.resources import Resource


class _ViewInstrumentMatch:
    def __init__(
        self,
        name: str,
        unit: str,
        description: str,
        attribute_keys: Dict[str, str],
        extra_dimensions: List[str],
        aggregation: Aggregation,
        exemplar_reservoir: Callable,
        resource: Resource,
    ):
        pass

    def _process(self, measurement: Measurement) -> None:
        pass

    def _collect(self, temporality: int) -> Iterable[Metric]:
        pass
