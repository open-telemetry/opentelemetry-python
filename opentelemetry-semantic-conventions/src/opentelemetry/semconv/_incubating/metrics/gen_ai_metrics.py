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


from typing import Final

from opentelemetry.metrics import Histogram, Meter

GEN_AI_CLIENT_OPERATION_DURATION: Final = "gen_ai.client.operation.duration"
"""
GenAI operation duration
Instrument: histogram
Unit: s
"""


# https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics/#metric-gen_aiclientoperationduration
_GEN_AI_CLIENT_OPERATION_DURATION_BUCKETS: Final = (
    0.01,
    0.02,
    0.04,
    0.08,
    0.16,
    0.32,
    0.64,
    1.28,
    2.56,
    5.12,
    10.24,
    20.48,
    40.96,
    81.92,
)


def create_gen_ai_client_operation_duration(meter: Meter) -> Histogram:
    """GenAI operation duration"""
    return meter.create_histogram(
        name=GEN_AI_CLIENT_OPERATION_DURATION,
        description="GenAI operation duration.",
        unit="s",
        explicit_bucket_boundaries_advisory=list(
            _GEN_AI_CLIENT_OPERATION_DURATION_BUCKETS
        ),
    )


GEN_AI_CLIENT_TOKEN_USAGE: Final = "gen_ai.client.token.usage"
"""
Number of input and output tokens used
Instrument: histogram
Unit: {token}
"""


def create_gen_ai_client_token_usage(meter: Meter) -> Histogram:
    """Number of input and output tokens used"""
    return meter.create_histogram(
        name=GEN_AI_CLIENT_TOKEN_USAGE,
        description="Number of input and output tokens used.",
        unit="{token}",
    )


GEN_AI_SERVER_REQUEST_DURATION: Final = "gen_ai.server.request.duration"
"""
Generative AI server request duration such as time-to-last byte or last output token
Instrument: histogram
Unit: s
"""


def create_gen_ai_server_request_duration(meter: Meter) -> Histogram:
    """Generative AI server request duration such as time-to-last byte or last output token"""
    # Shares the latency-style boundaries with client operation duration and
    # time-to-first-token per the semconv spec.
    return meter.create_histogram(
        name=GEN_AI_SERVER_REQUEST_DURATION,
        description="Generative AI server request duration such as time-to-last byte or last output token.",
        unit="s",
        explicit_bucket_boundaries_advisory=list(
            _GEN_AI_CLIENT_OPERATION_DURATION_BUCKETS
        ),
    )


GEN_AI_SERVER_TIME_PER_OUTPUT_TOKEN: Final = (
    "gen_ai.server.time_per_output_token"
)
"""
Time per output token generated after the first token for successful responses
Instrument: histogram
Unit: s
"""


# https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics/#metric-gen_aiservertime_per_output_token
_GEN_AI_SERVER_TIME_PER_OUTPUT_TOKEN_BUCKETS: Final = (
    0.01,
    0.025,
    0.05,
    0.075,
    0.1,
    0.15,
    0.2,
    0.3,
    0.4,
    0.5,
    0.75,
    1.0,
    2.5,
)


def create_gen_ai_server_time_per_output_token(meter: Meter) -> Histogram:
    """Time per output token generated after the first token for successful responses"""
    return meter.create_histogram(
        name=GEN_AI_SERVER_TIME_PER_OUTPUT_TOKEN,
        description="Time per output token generated after the first token for successful responses.",
        unit="s",
        explicit_bucket_boundaries_advisory=list(
            _GEN_AI_SERVER_TIME_PER_OUTPUT_TOKEN_BUCKETS
        ),
    )


GEN_AI_SERVER_TIME_TO_FIRST_TOKEN: Final = "gen_ai.server.time_to_first_token"
"""
Time to generate first token for successful responses
Instrument: histogram
Unit: s
"""


def create_gen_ai_server_time_to_first_token(meter: Meter) -> Histogram:
    """Time to generate first token for successful responses"""
    # Shares the latency-style boundaries with client operation duration per
    # the semconv spec.
    return meter.create_histogram(
        name=GEN_AI_SERVER_TIME_TO_FIRST_TOKEN,
        description="Time to generate first token for successful responses.",
        unit="s",
        explicit_bucket_boundaries_advisory=list(
            _GEN_AI_CLIENT_OPERATION_DURATION_BUCKETS
        ),
    )
