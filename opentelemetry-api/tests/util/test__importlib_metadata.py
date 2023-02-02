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

from unittest import TestCase
from warnings import catch_warnings, filterwarnings

from opentelemetry.metrics import MeterProvider
from opentelemetry.util._importlib_metadata import EntryPoint
from opentelemetry.util._importlib_metadata import (
    entry_points as entry_points_function,  # SelectableGroups,; EntryPoints
)


class TestEntryPoints(TestCase):
    def test_entry_points(self):

        self.assertIsInstance(
            next(
                iter(
                    entry_points_function(
                        group="opentelemetry_meter_provider",
                        name="default_meter_provider",
                    )
                )
            ).load()(),
            MeterProvider,
        )

    def test_uniform_behavior(self):
        """
        Test that entry_points behaves the same regardless of the Python
        version.
        """

        selectable_groups = entry_points_function()

        # self.assertIsInstance(selectable_groups, SelectableGroups)

        # Supressing the following warning here:
        # DeprecationWarning: SelectableGroups dict interface is deprecated. Use select.
        # The behavior of the importlib metadata library is hard to understand,
        # this is True: selectable_groups is selectable_groups.select(). So,
        # using select, as the warning says yields the same problem. Also
        # select does not accept any parameters.

        with catch_warnings():
            filterwarnings("ignore", category=DeprecationWarning)
            entry_points = selectable_groups.select()[
                "opentelemetry_propagator"
            ]

        # Supressing the following warning here:
        # DeprecationWarning: DeprecationWarning: Accessing entry points by index is deprecated. Cast to tuple if needed.
        # The behavior of the importlib metadata library is hard to understand,
        # this is True: entry_points == .select(). So, using select, as the
        # warning says yields the same problem. Also select does not accept any
        # parameters.
        with catch_warnings():
            filterwarnings("ignore", category=DeprecationWarning)

            self.assertIsInstance(entry_points.select()[0], EntryPoint)

            entry_points = entry_points_function(
                group="opentelemetry_propagator"
            )

            self.assertIsInstance(entry_points.select()[0], EntryPoint)

            entry_points = entry_points_function(
                group="opentelemetry_propagator", name="baggage"
            )

            self.assertIsInstance(entry_points.select()[0], EntryPoint)

        entry_points = entry_points_function(group="abc")

        self.assertEqual(entry_points, [])

        entry_points = entry_points_function(
            group="opentelemetry_propagator", name="abc"
        )

        self.assertEqual(entry_points, [])
