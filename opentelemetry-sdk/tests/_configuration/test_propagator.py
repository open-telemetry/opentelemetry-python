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
from os import environ
from unittest.mock import MagicMock, patch

# CompositePropagator stores its propagators in _propagators (private).
# We access it here to assert composition correctness.
# pylint: disable=protected-access
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.environment_variables import OTEL_PROPAGATORS
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.sdk._configuration._exceptions import ConfigurationError
from opentelemetry.sdk._configuration._propagator import (
    configure_propagator,
    create_propagator,
)
from opentelemetry.sdk._configuration.models import (
    Propagator as PropagatorConfig,
)
from opentelemetry.sdk._configuration.models import (
    TextMapPropagator as TextMapPropagatorConfig,
)
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
)


class TestCreatePropagator(unittest.TestCase):
    def test_none_config_returns_empty_composite(self):
        result = create_propagator(None)
        self.assertIsInstance(result, CompositePropagator)
        self.assertEqual(result._propagators, [])  # type: ignore[attr-defined]

    def test_empty_config_returns_empty_composite(self):
        result = create_propagator(PropagatorConfig())
        self.assertIsInstance(result, CompositePropagator)
        self.assertEqual(result._propagators, [])  # type: ignore[attr-defined]

    def test_tracecontext_only(self):
        config = PropagatorConfig(
            composite=[TextMapPropagatorConfig(tracecontext={})]
        )
        result = create_propagator(config)
        self.assertEqual(len(result._propagators), 1)  # type: ignore[attr-defined]
        self.assertIsInstance(
            result._propagators[0],
            TraceContextTextMapPropagator,  # type: ignore[attr-defined]
        )

    def test_baggage_only(self):
        config = PropagatorConfig(
            composite=[TextMapPropagatorConfig(baggage={})]
        )
        result = create_propagator(config)
        self.assertEqual(len(result._propagators), 1)  # type: ignore[attr-defined]
        self.assertIsInstance(result._propagators[0], W3CBaggagePropagator)  # type: ignore[attr-defined]

    def test_tracecontext_and_baggage(self):
        config = PropagatorConfig(
            composite=[
                TextMapPropagatorConfig(tracecontext={}),
                TextMapPropagatorConfig(baggage={}),
            ]
        )
        result = create_propagator(config)
        self.assertEqual(len(result._propagators), 2)  # type: ignore[attr-defined]
        self.assertIsInstance(
            result._propagators[0],
            TraceContextTextMapPropagator,  # type: ignore[attr-defined]
        )
        self.assertIsInstance(result._propagators[1], W3CBaggagePropagator)  # type: ignore[attr-defined]

    def test_b3_via_entry_point(self):
        mock_propagator = MagicMock()
        mock_ep = MagicMock()
        mock_ep.load.return_value = lambda: mock_propagator

        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[mock_ep],
        ):
            config = PropagatorConfig(
                composite=[TextMapPropagatorConfig(b3={})]
            )
            result = create_propagator(config)

        self.assertEqual(len(result._propagators), 1)  # type: ignore[attr-defined]
        self.assertIs(result._propagators[0], mock_propagator)  # type: ignore[attr-defined]

    def test_b3multi_via_entry_point(self):
        mock_propagator = MagicMock()
        mock_ep = MagicMock()
        mock_ep.load.return_value = lambda: mock_propagator

        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[mock_ep],
        ):
            config = PropagatorConfig(
                composite=[TextMapPropagatorConfig(b3multi={})]
            )
            result = create_propagator(config)

        self.assertEqual(len(result._propagators), 1)  # type: ignore[attr-defined]

    def test_b3_not_installed_raises_configuration_error(self):
        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[],
        ):
            config = PropagatorConfig(
                composite=[TextMapPropagatorConfig(b3={})]
            )
            with self.assertRaises(ConfigurationError) as ctx:
                create_propagator(config)
        self.assertIn("b3", str(ctx.exception))

    def test_composite_list_tracecontext(self):
        config = PropagatorConfig(composite_list="tracecontext")
        mock_tc = TraceContextTextMapPropagator()
        mock_ep = MagicMock()
        mock_ep.load.return_value = lambda: mock_tc

        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[mock_ep],
        ):
            result = create_propagator(config)

        self.assertEqual(len(result._propagators), 1)  # type: ignore[attr-defined]

    def test_composite_list_multiple(self):
        mock_tc = TraceContextTextMapPropagator()
        mock_baggage = W3CBaggagePropagator()
        mock_ep_tc = MagicMock()
        mock_ep_tc.load.return_value = lambda: mock_tc
        mock_ep_baggage = MagicMock()
        mock_ep_baggage.load.return_value = lambda: mock_baggage

        def fake_entry_points(group, name):
            if name == "tracecontext":
                return [mock_ep_tc]
            if name == "baggage":
                return [mock_ep_baggage]
            return []

        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            side_effect=fake_entry_points,
        ):
            config = PropagatorConfig(composite_list="tracecontext,baggage")
            result = create_propagator(config)

        self.assertEqual(len(result._propagators), 2)  # type: ignore[attr-defined]

    def test_composite_list_none_entry_skipped(self):
        config = PropagatorConfig(composite_list="none")
        result = create_propagator(config)
        self.assertEqual(result._propagators, [])  # type: ignore[attr-defined]

    def test_composite_list_empty_entries_skipped(self):
        config = PropagatorConfig(composite_list=",, ,")
        result = create_propagator(config)
        self.assertEqual(result._propagators, [])  # type: ignore[attr-defined]

    def test_composite_list_whitespace_around_names(self):
        mock_tc = TraceContextTextMapPropagator()
        mock_ep = MagicMock()
        mock_ep.load.return_value = lambda: mock_tc

        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[mock_ep],
        ):
            config = PropagatorConfig(composite_list=" tracecontext ")
            result = create_propagator(config)

        self.assertEqual(len(result._propagators), 1)  # type: ignore[attr-defined]

    def test_entry_point_load_exception_raises_configuration_error(self):
        mock_ep = MagicMock()
        mock_ep.load.side_effect = RuntimeError("package broken")

        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[mock_ep],
        ):
            config = PropagatorConfig(composite_list="broken-prop")
            with self.assertRaises(ConfigurationError) as ctx:
                create_propagator(config)
        self.assertIn("broken-prop", str(ctx.exception))

    def test_deduplication_across_composite_and_composite_list(self):
        """Same propagator type from both composite and composite_list is deduplicated."""
        mock_tc = TraceContextTextMapPropagator()
        mock_ep = MagicMock()
        mock_ep.load.return_value = lambda: mock_tc

        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[mock_ep],
        ):
            config = PropagatorConfig(
                composite=[TextMapPropagatorConfig(tracecontext={})],
                composite_list="tracecontext",
            )
            result = create_propagator(config)

        # Only one TraceContextTextMapPropagator despite being in both
        tc_count = sum(
            1
            for p in result._propagators  # type: ignore[attr-defined]
            if isinstance(p, TraceContextTextMapPropagator)
        )
        self.assertEqual(tc_count, 1)

    def test_unknown_composite_list_propagator_raises(self):
        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[],
        ):
            config = PropagatorConfig(composite_list="nonexistent")
            with self.assertRaises(ConfigurationError):
                create_propagator(config)

    def test_plugin_propagator_via_entry_point(self):
        mock_propagator = MagicMock()
        mock_ep = MagicMock()
        mock_ep.load.return_value = lambda: mock_propagator

        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[mock_ep],
        ):
            config = PropagatorConfig(
                composite=[
                    # pylint: disable=unexpected-keyword-arg
                    TextMapPropagatorConfig(my_custom_propagator={})
                ]
            )
            result = create_propagator(config)

        self.assertEqual(len(result._propagators), 1)  # type: ignore[attr-defined]
        self.assertIs(result._propagators[0], mock_propagator)  # type: ignore[attr-defined]

    def test_unknown_composite_propagator_raises(self):
        with patch(
            "opentelemetry.sdk._configuration._common.entry_points",
            return_value=[],
        ):
            config = PropagatorConfig(
                composite=[
                    # pylint: disable=unexpected-keyword-arg
                    TextMapPropagatorConfig(nonexistent={})
                ]
            )
            with self.assertRaises(ConfigurationError):
                create_propagator(config)


class TestConfigurePropagator(unittest.TestCase):
    def test_configure_propagator_calls_set_global_textmap(self):
        with patch(
            "opentelemetry.sdk._configuration._propagator.set_global_textmap"
        ) as mock_set:
            configure_propagator(None)
            mock_set.assert_called_once()
            arg = mock_set.call_args[0][0]
            self.assertIsInstance(arg, CompositePropagator)

    def test_configure_propagator_with_config(self):
        config = PropagatorConfig(
            composite=[TextMapPropagatorConfig(tracecontext={})]
        )
        with patch(
            "opentelemetry.sdk._configuration._propagator.set_global_textmap"
        ) as mock_set:
            configure_propagator(config)
            mock_set.assert_called_once()
            propagator = mock_set.call_args[0][0]
            self.assertIsInstance(propagator, CompositePropagator)
            self.assertEqual(len(propagator._propagators), 1)  # type: ignore[attr-defined]

    @patch.dict(environ, {OTEL_PROPAGATORS: "baggage"})
    def test_otel_propagators_env_var_ignored(self):
        """OTEL_PROPAGATORS env var must not influence configure_propagator output."""
        config = PropagatorConfig(
            composite=[TextMapPropagatorConfig(tracecontext={})]
        )
        with patch(
            "opentelemetry.sdk._configuration._propagator.set_global_textmap"
        ) as mock_set:
            configure_propagator(config)
            propagator = mock_set.call_args[0][0]
            self.assertEqual(len(propagator._propagators), 1)  # type: ignore[attr-defined]
            self.assertIsInstance(
                propagator._propagators[0],
                TraceContextTextMapPropagator,  # type: ignore[attr-defined]
            )
