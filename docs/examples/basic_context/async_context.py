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

import asyncio

from opentelemetry import baggage, trace
from opentelemetry.sdk.trace import TracerProvider

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

loop = asyncio.get_event_loop()


async def async_span(span):
    with tracer.use_span(span):
        ctx = baggage.set_baggage("foo", "bar")
    return ctx


async def main():
    span = tracer.start_span(name="span")
    ctx = await async_span(span)
    print(baggage.get_all(context=ctx))


loop.run_until_complete(main())
