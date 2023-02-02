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
# type: ignore

from unittest import TestCase

from opentelemetry.baggage import get_baggage, set_baggage
from opentelemetry.baggage.propagation import W3CBaggagePropagator


class TestBaggageManager(TestCase):
    def test_propagate_baggage(self):
        carrier = {}
        propagator = W3CBaggagePropagator()

        ctx = set_baggage("Test1", "value1")
        ctx = set_baggage("test2", "value2", context=ctx)

        propagator.inject(carrier, ctx)
        ctx_propagated = propagator.extract(carrier)

        self.assertEqual(
            get_baggage("Test1", context=ctx_propagated), "value1"
        )
        self.assertEqual(
            get_baggage("test2", context=ctx_propagated), "value2"
        )
