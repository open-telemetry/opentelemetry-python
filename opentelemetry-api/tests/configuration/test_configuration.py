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
# pylint: disable-all

from unittest import TestCase
from unittest.mock import patch

from opentelemetry.configuration import Configuration


class TestConfiguration(TestCase):
    def tearDown(self) -> None:
        # This call resets the attributes of the Configuration class so that
        # each test is executed in the same conditions.
        Configuration._reset()

    def test_singleton(self) -> None:
        self.assertIsInstance(Configuration(), Configuration)
        self.assertIs(Configuration(), Configuration())

    @patch.dict(
        "os.environ",  # type: ignore
        {
            "OPENTELEMETRY_PYTHON_METER_PROVIDER": "meter_provider",
            "OPENTELEMETRY_PYTHON_TRACER_PROVIDER": "tracer_provider",
            "OPENTELEMETRY_PYTHON_OThER": "other",
            "OPENTELEMETRY_PYTHON_OTHER_7": "other_7",
            "OPENTELEMETRY_PTHON_TRACEX_PROVIDER": "tracex_provider",
        },
    )
    def test_environment_variables(self):
        self.assertEqual(
            Configuration().METER_PROVIDER, "meter_provider"
        )  # pylint: disable=no-member
        self.assertEqual(
            Configuration().TRACER_PROVIDER, "tracer_provider"
        )  # pylint: disable=no-member
        self.assertEqual(
            Configuration().OThER, "other"
        )  # pylint: disable=no-member
        self.assertEqual(
            Configuration().OTHER_7, "other_7"
        )  # pylint: disable=no-member
        self.assertIsNone(Configuration().TRACEX_PROVIDER)

    @patch.dict(
        "os.environ",  # type: ignore
        {"OPENTELEMETRY_PYTHON_TRACER_PROVIDER": "tracer_provider"},
    )
    def test_property(self):
        with self.assertRaises(AttributeError):
            Configuration().TRACER_PROVIDER = "new_tracer_provider"

    def test_slots(self) -> None:
        with self.assertRaises(AttributeError):
            Configuration().XYZ = "xyz"  # pylint: disable=assigning-non-slot

    def test_getattr(self) -> None:
        # literal access
        self.assertIsNone(Configuration().XYZ)

        # dynamic access
        self.assertIsNone(getattr(Configuration(), "XYZ"))
        self.assertIsNone(Configuration().get("XYZ", None))

    def test_reset(self) -> None:
        environ_patcher = patch.dict(
            "os.environ",
            {"OPENTELEMETRY_PYTHON_TRACER_PROVIDER": "tracer_provider"},
        )

        environ_patcher.start()

        self.assertEqual(
            Configuration().TRACER_PROVIDER, "tracer_provider"
        )  # pylint: disable=no-member

        environ_patcher.stop()

        Configuration._reset()

        self.assertIsNone(
            Configuration().TRACER_PROVIDER
        )  # pylint: disable=no-member

    @patch.dict(
        "os.environ",  # type: ignore
        {
            "OPENTELEMETRY_PYTHON_TRUE": "True",
            "OPENTELEMETRY_PYTHON_FALSE": "False",
        },
    )
    def test_boolean(self) -> None:
        self.assertIsInstance(
            Configuration().TRUE, bool
        )  # pylint: disable=no-member
        self.assertIsInstance(
            Configuration().FALSE, bool
        )  # pylint: disable=no-member
        self.assertTrue(Configuration().TRUE)  # pylint: disable=no-member
        self.assertFalse(Configuration().FALSE)  # pylint: disable=no-member

    @patch.dict(
        "os.environ",  # type: ignore
        {
            "OPENTELEMETRY_PYTHON_POSITIVE_INTEGER": "123",
            "OPENTELEMETRY_PYTHON_NEGATIVE_INTEGER": "-123",
            "OPENTELEMETRY_PYTHON_NON_INTEGER": "-12z3",
        },
    )
    def test_integer(self) -> None:
        self.assertEqual(
            Configuration().POSITIVE_INTEGER, 123
        )  # pylint: disable=no-member
        self.assertEqual(
            Configuration().NEGATIVE_INTEGER, -123
        )  # pylint: disable=no-member
        self.assertEqual(
            Configuration().NON_INTEGER, "-12z3"
        )  # pylint: disable=no-member

    @patch.dict(
        "os.environ",  # type: ignore
        {
            "OPENTELEMETRY_PYTHON_POSITIVE_FLOAT": "123.123",
            "OPENTELEMETRY_PYTHON_NEGATIVE_FLOAT": "-123.123",
            "OPENTELEMETRY_PYTHON_NON_FLOAT": "-12z3.123",
        },
    )
    def test_float(self) -> None:
        self.assertEqual(
            Configuration().POSITIVE_FLOAT, 123.123
        )  # pylint: disable=no-member
        self.assertEqual(
            Configuration().NEGATIVE_FLOAT, -123.123
        )  # pylint: disable=no-member
        self.assertEqual(
            Configuration().NON_FLOAT, "-12z3.123"
        )  # pylint: disable=no-member
