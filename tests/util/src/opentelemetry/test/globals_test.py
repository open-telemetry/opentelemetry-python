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

import unittest

from opentelemetry import trace as trace_api
from opentelemetry.util._once import Once


# pylint: disable=protected-access
def reset_trace_globals() -> None:
    """WARNING: only use this for tests."""
    trace_api._TRACER_PROVIDER_SET_ONCE = Once()
    trace_api._TRACER_PROVIDER = None
    trace_api._PROXY_TRACER_PROVIDER = trace_api.ProxyTracerProvider()


class TraceGlobalsTestMixin(unittest.TestCase):
    """Resets trace API globals in setUp/tearDown

    Use as a mixin with unittest.TestCase for your test that modifies trace API
    globals.
    """

    def setUp(self) -> None:
        if hasattr(super(), "setUp"):
            super().setUp()
        reset_trace_globals()

    def tearDown(self) -> None:
        if hasattr(super(), "tearDown"):
            super().tearDown()
        reset_trace_globals()
