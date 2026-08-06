# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import opentelemetry.propagators.b3 as b3_format
from opentelemetry.sdk.trace import TracerProvider

FORMAT = b3_format.B3Format()


def test_extract_single_header(benchmark):
    benchmark(
        FORMAT.extract,
        {
            FORMAT.SINGLE_HEADER_KEY: "bdb5b63237ed38aea578af665aa5aa60-c32d953d73ad2251-1"
        },
    )


def test_inject_empty_context(benchmark):
    tracer = TracerProvider().get_tracer("sdk_tracer_provider")
    with tracer.start_as_current_span("Root Span"):
        with tracer.start_as_current_span("Child Span"):
            benchmark(
                FORMAT.inject,
                {
                    FORMAT.TRACE_ID_KEY: "bdb5b63237ed38aea578af665aa5aa60",
                    FORMAT.SPAN_ID_KEY: "00000000000000000c32d953d73ad225",
                    FORMAT.SAMPLED_KEY: "1",
                },
            )
