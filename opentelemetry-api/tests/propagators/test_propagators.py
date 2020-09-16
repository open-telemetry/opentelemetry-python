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

from importlib import reload
from unittest import TestCase
from unittest.mock import patch

from opentelemetry.baggage.propagation import BaggagePropagator
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
)


class TestPropagators(TestCase):
    @patch("opentelemetry.propagators.composite.CompositeHTTPPropagator")
    def test_default_composite_propagators(self, mock_compositehttppropagator):
        def test_propagators(propagators):

            propagators = {propagator.__class__ for propagator in propagators}

            self.assertEqual(len(propagators), 2)
            self.assertEqual(
                propagators, {TraceContextTextMapPropagator, BaggagePropagator}
            )

        mock_compositehttppropagator.configure_mock(
            **{"side_effect": test_propagators}
        )

        import opentelemetry.propagators

        reload(opentelemetry.propagators)
