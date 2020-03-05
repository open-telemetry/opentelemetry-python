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

from opentelemetry.configuration import Configuration
from pytest import fixture  # pylint: disable=import-error


class TestConfiguration(TestCase):
    @fixture(autouse=True)
    def configdir(self, tmpdir):  # pylint: disable=no-self-use
        tmpdir.chdir()
        tmpdir.mkdir(".config").join("opentelemetry_python.json").write(
            dumps(
                {
                    "tracer": "default_tracer",
                    "exporter": "overridden_exporter",
                }
            )
        )

    def setUp(self):
        Configuration._instance = None  # pylint: disable=protected-access

    def tearDown(self):
        Configuration._instance = None  # pylint: disable=protected-access

    def test_singleton(self):
        self.assertIs(Configuration(), Configuration())

    @patch("pathlib.Path.home")
    def test_configuration_file(self, mock_home_path):
        mock_home_path.return_value = getcwd()

        self.assertEqual(
            Configuration().tracer, "default_tracer"
        )  # pylint: disable=no-member
        self.assertEqual(
            Configuration().exporter, "overridden_exporter"
        )  # pylint: disable=no-member
        self.assertEqual(
            Configuration().context, "default_context"
        )  # pylint: disable=no-member

    @patch.dict(
        "os.environ", {"OPENTELEMETRY_PYTHON_EXPORTER": "overridden_exporter"}
    )
    def test_environment_variables(self):
        self.assertEqual(
            Configuration().tracer, "default_tracer"
        )  # pylint: disable=no-member
        self.assertEqual(
            Configuration().exporter, "overridden_exporter"
        )  # pylint: disable=no-member
        self.assertEqual(
            Configuration().context, "default_context"
        )  # pylint: disable=no-member

    @patch("pathlib.Path.home")
    @patch.dict(
        "os.environ",
        {"OPENTELEMETRY_PYTHON_EXPORTER": "reoverridden_exporter"},
    )
    def test_configuration_file_environment_variables(self, mock_home_path):
        mock_home_path.return_value = getcwd()

        self.assertEqual(Configuration().tracer, "default_tracer")
        self.assertEqual(Configuration().exporter, "reoverridden_exporter")
        self.assertEqual(Configuration().context, "default_context")

    def test_property(self):
        with self.assertRaises(AttributeError):
            Configuration().tracer = "new_tracer"

    def test_slots(self):
        with self.assertRaises(AttributeError):
            Configuration().xyz = "xyz"  # pylint: disable=assigning-non-slot
