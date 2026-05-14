# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import asyncio

from opentelemetry import baggage, trace
from opentelemetry.sdk.trace import TracerProvider

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

loop = asyncio.get_event_loop()


async def async_span(span):
    with trace.use_span(span):
        ctx = baggage.set_baggage("foo", "bar")
    return ctx


async def main():
    span = tracer.start_span(name="span")
    ctx = await async_span(span)
    print(baggage.get_all(context=ctx))


loop.run_until_complete(main())
