# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase

from opentelemetry.metrics import MeterProvider
from opentelemetry.util._importlib_metadata import (
    EntryPoint,
    EntryPoints,
    version,
)
from opentelemetry.util._importlib_metadata import (
    entry_points as importlib_metadata_entry_points,
)


class TestEntryPoints(TestCase):
    def test_entry_points(self):
        self.assertIsInstance(
            next(
                iter(
                    importlib_metadata_entry_points(
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

        entry_points = importlib_metadata_entry_points()

        self.assertIsInstance(entry_points, EntryPoints)

        entry_points = entry_points.select(group="opentelemetry_propagator")
        self.assertIsInstance(entry_points, EntryPoints)

        entry_points = entry_points.select(name="baggage")
        self.assertIsInstance(entry_points, EntryPoints)

        entry_point = next(iter(entry_points))
        self.assertIsInstance(entry_point, EntryPoint)

        self.assertEqual(entry_point.name, "baggage")
        self.assertEqual(entry_point.group, "opentelemetry_propagator")
        self.assertEqual(
            entry_point.value,
            "opentelemetry.baggage.propagation:W3CBaggagePropagator",
        )

        entry_points = importlib_metadata_entry_points(
            group="opentelemetry_propagator"
        )
        self.assertIsInstance(entry_points, EntryPoints)

        entry_points = entry_points.select(name="baggage")
        self.assertIsInstance(entry_points, EntryPoints)

        entry_point = next(iter(entry_points))
        self.assertIsInstance(entry_point, EntryPoint)

        self.assertEqual(entry_point.name, "baggage")
        self.assertEqual(entry_point.group, "opentelemetry_propagator")
        self.assertEqual(
            entry_point.value,
            "opentelemetry.baggage.propagation:W3CBaggagePropagator",
        )

        entry_points = importlib_metadata_entry_points(name="baggage")
        self.assertIsInstance(entry_points, EntryPoints)

        entry_point = next(iter(entry_points))
        self.assertIsInstance(entry_point, EntryPoint)

        self.assertEqual(entry_point.name, "baggage")
        self.assertEqual(entry_point.group, "opentelemetry_propagator")
        self.assertEqual(
            entry_point.value,
            "opentelemetry.baggage.propagation:W3CBaggagePropagator",
        )

        entry_points = importlib_metadata_entry_points(group="abc")
        self.assertIsInstance(entry_points, EntryPoints)
        self.assertEqual(len(entry_points), 0)

        entry_points = importlib_metadata_entry_points(
            group="opentelemetry_propagator", name="abc"
        )
        self.assertIsInstance(entry_points, EntryPoints)
        self.assertEqual(len(entry_points), 0)

        entry_points = importlib_metadata_entry_points(group="abc", name="abc")
        self.assertIsInstance(entry_points, EntryPoints)
        self.assertEqual(len(entry_points), 0)

        self.assertIsInstance(version("opentelemetry-api"), str)
