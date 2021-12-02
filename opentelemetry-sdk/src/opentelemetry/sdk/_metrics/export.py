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
from typing import Union

# FIXME this is being copied directly from
# opentelemetry.proto.metrics.v1.metrics_pb2. The only reason for doing so is
# to avoid havinv protobuf as a indirect dependency in the SDK. This
# duplication of code is not ideal.

AGGREGATION_TEMPORALITY_UNSPECIFIED = 0
AGGREGATION_TEMPORALITY_DELTA = 1
AGGREGATION_TEMPORALITY_CUMULATIVE = 2


@dataclass(frozen=True)
class Sum:
    aggregation_temporality: int
    is_monotonic: bool
    start_time_unix_nano: int
    time_unix_nano: int
    value: Union[int, float]


@dataclass(frozen=True)
class Gauge:
    time_unix_nano: int
    value: Union[int, float]


PointT = Union[Sum, Gauge]
