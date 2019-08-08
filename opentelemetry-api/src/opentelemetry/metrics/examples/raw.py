# Copyright 2019, OpenTelemetry Authors
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

import psutil
import time

from opentelemetry.distributedcontext import DistributedContext
from opentelemetry.metrics import Meter

meter = Meter()
measure = meter.create_float_measure("cpu_usage", "cpu usage over time", "percentage")

measurements = []
for i in range(100):
    measurements.append(measure.createMeasurement(psutil.cpu_percent()))
    time.sleep(1)

    meter.record(measurements, distributed_context=DistributedContext.get_current())