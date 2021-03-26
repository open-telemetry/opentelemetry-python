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

import opentelemetry.propagators.b3 as b3_format
import opentelemetry.sdk.trace as trace

FORMAT = b3_format.B3Format()


def test_extract_single_header(benchmark):
    benchmark(
        FORMAT.extract,
        {
            FORMAT.SINGLE_HEADER_KEY: "bdb5b63237ed38aea578af665aa5aa60-c32d953d73ad2251-1-11fd79a30b0896cd285b396ae102dd76"
        },
    )


def test_inject_empty_context(benchmark):
    tracer = trace.TracerProvider().get_tracer("sdk_tracer_provider")
    with tracer.start_as_current_span("Root Span"):
        with tracer.start_as_current_span("Child Span"):
            benchmark(
                FORMAT.inject,
                {
                    FORMAT.TRACE_ID_KEY: "bdb5b63237ed38aea578af665aa5aa60",
                    FORMAT.SPAN_ID_KEY: "00000000000000000c32d953d73ad225",
                    FORMAT.PARENT_SPAN_ID_KEY: "11fd79a30b0896cd285b396ae102dd76",
                    FORMAT.SAMPLED_KEY: "1",
                },
            )
