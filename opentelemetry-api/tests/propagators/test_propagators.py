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

# type: ignore

from importlib import reload
from os import environ
from unittest import TestCase
from unittest.mock import Mock, patch

from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.environment_variables import OTEL_PROPAGATORS
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
)


class TestPropagators(TestCase):
    @patch("opentelemetry.propagators.composite.CompositePropagator")
    def test_default_composite_propagators(self, mock_compositehttppropagator):
        def test_propagators(propagators):

            propagators = {propagator.__class__ for propagator in propagators}

            self.assertEqual(len(propagators), 2)
            self.assertEqual(
                propagators,
                {TraceContextTextMapPropagator, W3CBaggagePropagator},
            )

        mock_compositehttppropagator.configure_mock(
            **{"side_effect": test_propagators}
        )

        import opentelemetry.propagate

        reload(opentelemetry.propagate)

    @patch.dict(environ, {OTEL_PROPAGATORS: "a,b,c"})
    @patch("opentelemetry.propagators.composite.CompositePropagator")
    @patch("pkg_resources.iter_entry_points")
    def test_non_default_propagators(
        self, mock_iter_entry_points, mock_compositehttppropagator
    ):
        def iter_entry_points_mock(_, propagator):
            return iter(
                [
                    Mock(
                        **{
                            "load.side_effect": [
                                Mock(**{"side_effect": [propagator]})
                            ]
                        }
                    )
                ]
            )

        mock_iter_entry_points.configure_mock(
            **{"side_effect": iter_entry_points_mock}
        )

        def test_propagators(propagators):

            self.assertEqual(propagators, ["a", "b", "c"])

        mock_compositehttppropagator.configure_mock(
            **{"side_effect": test_propagators}
        )

        import opentelemetry.propagate

        reload(opentelemetry.propagate)
