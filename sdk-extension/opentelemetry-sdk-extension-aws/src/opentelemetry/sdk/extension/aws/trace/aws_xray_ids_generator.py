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

import datetime
import random

from opentelemetry import trace

EPOCH = datetime.datetime.utcfromtimestamp(0)


class AWSXRayIdsGenerator(trace.IdsGenerator):
    """Generates tracing IDs compatible with the AWS X-Ray tracing service. In
    the X-Ray system, the first 32 bits of the `TraceId` are the Unix epoch time
    in seconds. Since spans (AWS calls them segments) with an embedded timestamp
    more than 30 days ago are rejected, a purely random `TraceId` risks being
    rejected by the service.

    See: https://docs.aws.amazon.com/xray/latest/devguide/xray-api-sendingdata.html#xray-api-traceids
    """

    def generate_span_id(self) -> int:
        return trace.RandomIdsGenerator().generate_span_id()

    def generate_trace_id(self) -> int:
        trace_time = int(datetime.datetime.now().timestamp())
        trace_identifier = random.getrandbits(96)
        return (trace_time << 96) + trace_identifier
