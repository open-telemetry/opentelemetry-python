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

from sys import version_info
from unittest import TestCase

from opentelemetry.metrics import MeterProvider
from opentelemetry.util._importlib_metadata import EntryPoint, EntryPoints
from opentelemetry.util._importlib_metadata import (
    entry_points as importlib_metadata_entry_points,
)
from opentelemetry.util._importlib_metadata import version


class TestDependencies(TestCase):

    def test_dependencies(self):

        # pylint: disable=import-outside-toplevel
        # pylint: disable=unused-import
        # pylint: disable=import-error
        if version_info.minor < 10:
            try:
                import importlib_metadata  # type: ignore

            except ImportError:
                self.fail(
                    "importlib_metadata not installed when testing with "
                    f"{version_info.major}.{version_info.minor}"
                )

        else:
            try:
                import importlib_metadata  # noqa

            except ImportError:
                pass

            else:
                self.fail(
                    "importlib_metadata installed when testing with "
                    f"{version_info.major}.{version_info.minor}"
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

        importlib.metadata was introduced in 3.8 as a replacement for
        pkg_resources. The problem is that the API of importlib.metadata
        changed in subsequent versions.

        For example, in 3.8 or 3.9 importlib.metadata.entry_points does not
        support the keyword arguments group or name, but those keyword
        arguments are supported in 3.10, 3.11 and 3.12.

        There exists a package named importlib-metadata that has an API that
        includes a function named importlib_metadata.entry_points which
        supports the keyword arguments group and name, so we use
        importlib_metadata.entry_points when running in 3.8 or 3.9.

        importlib_metadata.entry_points and importlib.metadata.entry_points do
        not return objects of the same type when called without any arguments.
        That is why the implementation of the
        opentelemetry.util._importlib_metadata redefines entry_points so that
        it is mandatory to use an argument.
        """

        with self.assertRaises(ValueError):
            importlib_metadata_entry_points()

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
