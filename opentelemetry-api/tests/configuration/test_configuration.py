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

    # These calls reset the attributes of the Configuration class so that each
    # test is executed in the same conditions.
    def setUp(self) -> None:
        Configuration._reset()

    def test_singleton(self) -> None:
        self.assertIsInstance(Configuration(), Configuration)
        self.assertIs(Configuration(), Configuration())

    @patch.dict(
        "os.environ",  # type: ignore
        {
            "OTEL_PYTHON_METER_PROVIDER": "meter_provider",
            "OTEL_PYTHON_TRACER_PROVIDER": "tracer_provider",
            "OTEL_OThER": "other",
            "OTEL_OTHER_7": "other_7",
            "OPENTELEMETRY_PTHON_TRACEX_PROVIDER": "tracex_provider",
        },
    )
    def test_environment_variables(self) -> None:
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
        {"OTEL_PYTHON_TRACER_PROVIDER": "tracer_provider"},
    )
    def test_property(self) -> None:
        with self.assertRaises(AttributeError):
            Configuration().TRACER_PROVIDER = "new_tracer_provider"

    def test_set_once(self) -> None:

        Configuration().XYZ = "xyz"

        with self.assertRaises(AttributeError):
            Configuration().XYZ = "abc"  # pylint: disable=assigning-non-slot

    def test_getattr(self) -> None:
        # literal access
        self.assertIsNone(Configuration().XYZ)

        # dynamic access
        self.assertIsNone(getattr(Configuration(), "XYZ"))
        self.assertIsNone(Configuration().get("XYZ", None))

    def test_reset(self) -> None:
        environ_patcher = patch.dict(
            "os.environ", {"OTEL_PYTHON_TRACER_PROVIDER": "tracer_provider"},
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
        {"OTEL_TRUE": "True", "OTEL_FALSE": "False"},
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
            "OTEL_POSITIVE_INTEGER": "123",
            "OTEL_NEGATIVE_INTEGER": "-123",
            "OTEL_NON_INTEGER": "-12z3",
        },
    )
    def test_integer(self) -> None:
        # pylint: disable=no-member
        self.assertIsInstance(Configuration().POSITIVE_INTEGER, int)
        self.assertEqual(Configuration().POSITIVE_INTEGER, 123)
        self.assertIsInstance(Configuration().NEGATIVE_INTEGER, int)
        self.assertEqual(Configuration().NEGATIVE_INTEGER, -123)
        self.assertEqual(Configuration().NON_INTEGER, "-12z3")

    @patch.dict(
        "os.environ",  # type: ignore
        {
            "OTEL_POSITIVE_FLOAT": "123.123",
            "OTEL_NEGATIVE_FLOAT": "-123.123",
            "OTEL_NON_FLOAT": "-12z3.123",
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
