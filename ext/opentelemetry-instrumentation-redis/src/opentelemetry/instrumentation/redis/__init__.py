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
#
"""
Instrument `redis`_ to report Redis queries.

There are two options for instrumenting code. The first option is to use
the `opentelemetry-auto-instrumentation` executable which will automatically
patch your Redis client. The second is to programmatically enable
instrumentation via the following code:

.. _redis: https://pypi.org/project/redis/

Usage
-----

.. code:: python

    from opentelemetry import trace
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.sdk.trace import TracerProvider
    import redis

    trace.set_tracer_provider(TracerProvider())

    # You can patch redis specifically
    RedisInstrumentor().instrument(tracer_provider=trace.get_tracer_provider())

    # This will report a span with the default settings
    client = redis.StrictRedis(host="localhost", port=6379)
    client.get("my-key")

API
---
"""
from opentelemetry import trace
from opentelemetry.auto_instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.instrumentation.redis.patch import _patch, _unpatch


class RedisInstrumentor(BaseInstrumentor):
    """An instrumentor for Redis
    See `BaseInstrumentor`
    """

    def _instrument(self, **kwargs):
        _patch(
            tracer_provider=kwargs.get(
                "tracer_provider", trace.get_tracer_provider()
            )
        )

    def _uninstrument(self, **kwargs):
        _unpatch()
