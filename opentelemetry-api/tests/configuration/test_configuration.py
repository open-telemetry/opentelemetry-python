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
from unittest.mock import patch

from opentelemetry.configuration import Configuration  # type: ignore


class TestConfiguration(TestCase):

    def setUp(self):
        from opentelemetry.configuration import Configuration

    def tearDown(self):
        from opentelemetry.configuration import Configuration

    def test_singleton(self):
        self.assertIsInstance(Configuration(), Configuration)
        self.assertIs(Configuration(), Configuration())

    @patch.dict(
        "os.environ",
        {
            "OPENTELEMETRY_PYTHON_METER_PROVIDER": "meter_provider",
            "OPENTELEMETRY_PYTHON_TRACER_PROVIDER": "tracer_provider",
        },
    )
    def test_environment_variables(self):  # type: ignore
        self.assertEqual(
            Configuration().meter_provider, "meter_provider"
        )  # pylint: disable=no-member
        self.assertEqual(
            Configuration().tracer_provider, "tracer_provider"
        )  # pylint: disable=no-member

    def test_property(self):
        with self.assertRaises(AttributeError):
            Configuration().tracer_provider = "new_tracer_provider"

    def test_slots(self):
        with self.assertRaises(AttributeError):
            Configuration().xyz = "xyz"  # pylint: disable=assigning-non-slot
