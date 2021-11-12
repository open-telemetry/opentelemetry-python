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

from opentelemetry import _metrics as metrics_api
from opentelemetry import trace as trace_api
from opentelemetry.util._once import Once


# pylint: disable=protected-access
def reset_trace_globals() -> None:
    """WARNING: only use this for tests."""
    trace_api._TRACER_PROVIDER_SET_ONCE = Once()
    trace_api._TRACER_PROVIDER = None
    trace_api._PROXY_TRACER_PROVIDER = trace_api.ProxyTracerProvider()


# pylint: disable=protected-access
def reset_metrics_globals() -> None:
    """WARNING: only use this for tests."""
    metrics_api._METER_PROVIDER_SET_ONCE = Once()  # type: ignore[attr-defined]
    metrics_api._METER_PROVIDER = None  # type: ignore[attr-defined]
    metrics_api._PROXY_METER_PROVIDER = metrics_api._ProxyMeterProvider()  # type: ignore[attr-defined]


class TraceGlobalsTest(unittest.TestCase):
    """Resets trace API globals in setUp/tearDown

    Use as a base class or mixin for your test that modifies trace API globals.
    """

    def setUp(self) -> None:
        super().setUp()
        reset_trace_globals()

    def tearDown(self) -> None:
        super().tearDown()
        reset_trace_globals()


class MetricsGlobalsTest(unittest.TestCase):
    """Resets metrics API globals in setUp/tearDown

    Use as a base class or mixin for your test that modifies metrics API globals.
    """

    def setUp(self) -> None:
        super().setUp()
        reset_metrics_globals()

    def tearDown(self) -> None:
        super().tearDown()
        reset_metrics_globals()
