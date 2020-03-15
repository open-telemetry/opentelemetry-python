# Copyright 2020, OpenTelemetry Authors
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

from json import dumps
from unittest import TestCase
from unittest.mock import patch

from opentelemetry.configuration import Configuration  # type: ignore
from pytest import fixture  # type: ignore # pylint: disable=import-error


class TestConfiguration(TestCase):
    class IterEntryPointsMock:
        def __init__(
            self, argument, name=None
        ):  # pylint: disable=unused-argument
            self._name = name

        def __next__(self):
            return self

        def __call__(self):
            return self._name

        def load(self):
            return self

    @fixture(autouse=True)
    def configdir(self, tmpdir):  # type: ignore # pylint: disable=no-self-use
        tmpdir.chdir()
        tmpdir.mkdir(".config").join("opentelemetry_python.json").write(
            dumps({"tracer_provider": "overridden_tracer_provider"})
        )

    def setUp(self):
        Configuration._instance = None  # pylint: disable=protected-access

    def tearDown(self):
        Configuration._instance = None  # pylint: disable=protected-access

    def test_singleton(self):
        self.assertIs(Configuration(), Configuration())

    @patch(
        "opentelemetry.configuration.iter_entry_points",
        **{"side_effect": IterEntryPointsMock}  # type: ignore
    )
    def test_lazy(  # type: ignore
        self, mock_iter_entry_points,  # pylint: disable=unused-argument
    ):
        configuration = Configuration()

        self.assertIsNone(
            configuration._tracer_provider  # pylint: disable=no-member,protected-access
        )

        configuration.tracer_provider  # pylint: disable=pointless-statement

        self.assertEqual(
            configuration._tracer_provider,  # pylint: disable=no-member,protected-access
            "default_tracer_provider",
        )

    @patch(
        "opentelemetry.configuration.iter_entry_points",
        **{"side_effect": IterEntryPointsMock}  # type: ignore
    )
    def test_default_values(  # type: ignore
        self, mock_iter_entry_points  # pylint: disable=unused-argument
    ):
        self.assertEqual(
            Configuration().tracer_provider, "default_tracer_provider"
        )  # pylint: disable=no-member
        self.assertEqual(
            Configuration().meter_provider, "default_meter_provider"
        )  # pylint: disable=no-member

    @patch(
        "opentelemetry.configuration.iter_entry_points",
        **{"side_effect": IterEntryPointsMock}  # type: ignore
    )
    @patch.dict(
        "os.environ",
        {"OPENTELEMETRY_PYTHON_METER_PROVIDER": "overridden_meter_provider"},
    )
    def test_environment_variables(  # type: ignore
        self, mock_iter_entry_points  # pylint: disable=unused-argument
    ):  # type: ignore
        self.assertEqual(
            Configuration().tracer_provider, "default_tracer_provider"
        )  # pylint: disable=no-member
        self.assertEqual(
            Configuration().meter_provider, "overridden_meter_provider"
        )  # pylint: disable=no-member

    def test_property(self):
        with self.assertRaises(AttributeError):
            Configuration().tracer_provider = "new_tracer_provider"

    def test_slots(self):
        with self.assertRaises(AttributeError):
            Configuration().xyz = "xyz"  # pylint: disable=assigning-non-slot
