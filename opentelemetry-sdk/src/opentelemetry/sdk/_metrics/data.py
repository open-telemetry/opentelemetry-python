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

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo

class Metric:
    """ TODO fill this in """
    def __init__(self, resource: Resource) -> None:
        self.resource = resource

class MetricData:
    """ TODO fill this in """
    """Readable Metric data plus associated InstrumentationLibrary."""

    def __init__(
        self,
        metric: Metric,
        instrumentation_info: InstrumentationInfo,
    ):
        self.metric = metric
        self.instrumentation_info = instrumentation_info

