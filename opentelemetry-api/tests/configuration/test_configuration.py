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
from os import getcwd
from unittest import TestCase
from unittest.mock import patch

from opentelemetry.configuration import Configuration  # type: ignore
from pytest import fixture  # type: ignore # pylint: disable=import-error


class TestConfiguration(TestCase):
    @fixture(autouse=True)
    def configdir(self, tmpdir):  # type: ignore # pylint: disable=no-self-use
        tmpdir.chdir()
        tmpdir.mkdir(".config").join("opentelemetry_python.json").write(
            dumps({"tracer_provider": "default_tracer_provider"})
        )

    def setUp(self):
        Configuration._instance = None  # pylint: disable=protected-access

    def tearDown(self):
        Configuration._instance = None  # pylint: disable=protected-access

    def test_singleton(self):
        self.assertIs(Configuration(), Configuration())

    @patch("os.path.expanduser")
    def test_configuration_file(self, mock_expanduser):  # type: ignore
        mock_expanduser.return_value = getcwd()

        self.assertEqual(
            Configuration().tracer_provider, "default_tracer_provider"
        )  # pylint: disable=no-member
        self.assertEqual(
            Configuration().meter_provider, "default_meter_provider"
        )  # pylint: disable=no-member

    @patch.dict(
        "os.environ",
        {"OPENTELEMETRY_PYTHON_METER_PROVIDER": "overridden_meter_provider"},
    )
    def test_environment_variables(self):  # type: ignore
        self.assertEqual(
            Configuration().tracer_provider, "default_tracer_provider"
        )  # pylint: disable=no-member
        self.assertEqual(
            Configuration().meter_provider, "overridden_meter_provider"
        )  # pylint: disable=no-member

    @patch("os.path.expanduser")
    @patch.dict(
        "os.environ",
        {"OPENTELEMETRY_PYTHON_METER_PROVIDER": "reoverridden_meter_provider"},
    )
    def test_configuration_file_environment_variables(self, mock_expanduser):  # type: ignore
        mock_expanduser.return_value = getcwd()

        self.assertEqual(
            Configuration().tracer_provider, "default_tracer_provider"
        )
        self.assertEqual(
            Configuration().meter_provider, "reoverridden_meter_provider"
        )

    def test_property(self):
        with self.assertRaises(AttributeError):
            Configuration().tracer_provider = "new_tracer_provider"

    def test_slots(self):
        with self.assertRaises(AttributeError):
            Configuration().xyz = "xyz"  # pylint: disable=assigning-non-slot
