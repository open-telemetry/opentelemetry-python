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

from opentelemetry.jaeger_remote_sampling.local_agent_net import LocalAgentSender, LocalAgentHTTP
from opentelemetry.jaeger_remote_sampling.rate_limiter import RateLimiter
from opentelemetry.jaeger_remote_sampling.sampling import (
    get_rate_limit,
    get_sampling_probability,
    AdaptiveSampler,
    GuaranteedThroughputProbabilisticSampler,
    RateLimitingSampler,
    RemoteControlledSampler,
)