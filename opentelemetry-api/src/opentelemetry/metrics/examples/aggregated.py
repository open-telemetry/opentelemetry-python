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

from opentelemetry.distributedcontext import DistributedContext
from opentelemetry.metrics import Meter
from opentelemetry.metrics.label_key import LabelKey

meter = Meter()
label_keys = [LabelKey("environment", "the environment the application is running in")]
memory_metric = meter.create_int_gauge("available_memory", "available memory over time", "bytes", label_keys)
label_values = ["Testing"]
memory_metric.setCallBack(lambda: memory_metric.getOrCreateTimeSeries(label_values).set(psutil.virtual_memory().available))