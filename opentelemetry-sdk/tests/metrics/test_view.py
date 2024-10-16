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

# pylint: disable=protected-access

from unittest import TestCase
from unittest.mock import Mock

from opentelemetry.sdk.metrics.view import View


class TestView(TestCase):
    def test_required_instrument_criteria(self):
        with self.assertRaises(Exception):
            View()

    def test_instrument_type(self):
        self.assertTrue(View(instrument_type=Mock)._match(Mock()))

    def test_instrument_name(self):
        mock_instrument = Mock()
        mock_instrument.configure_mock(**{"name": "instrument_name"})

        self.assertTrue(
            View(instrument_name="instrument_name")._match(mock_instrument)
        )

    def test_instrument_unit(self):
        mock_instrument = Mock()
        mock_instrument.configure_mock(**{"unit": "instrument_unit"})

        self.assertTrue(
            View(instrument_unit="instrument_unit")._match(mock_instrument)
        )

    def test_meter_name(self):
        self.assertTrue(
            View(meter_name="meter_name")._match(
                Mock(**{"instrumentation_scope.name": "meter_name"})
            )
        )

    def test_meter_version(self):
        self.assertTrue(
            View(meter_version="meter_version")._match(
                Mock(**{"instrumentation_scope.version": "meter_version"})
            )
        )

    def test_meter_schema_url(self):
        self.assertTrue(
            View(meter_schema_url="meter_schema_url")._match(
                Mock(
                    **{"instrumentation_scope.schema_url": "meter_schema_url"}
                )
            )
        )
        self.assertFalse(
            View(meter_schema_url="meter_schema_url")._match(
                Mock(
                    **{
                        "instrumentation_scope.schema_url": "meter_schema_urlabc"
                    }
                )
            )
        )
        self.assertTrue(
            View(meter_schema_url="meter_schema_url")._match(
                Mock(
                    **{"instrumentation_scope.schema_url": "meter_schema_url"}
                )
            )
        )

    def test_additive_criteria(self):
        view = View(
            meter_name="meter_name",
            meter_version="meter_version",
            meter_schema_url="meter_schema_url",
        )

        self.assertTrue(
            view._match(
                Mock(
                    **{
                        "instrumentation_scope.name": "meter_name",
                        "instrumentation_scope.version": "meter_version",
                        "instrumentation_scope.schema_url": "meter_schema_url",
                    }
                )
            )
        )
        self.assertFalse(
            view._match(
                Mock(
                    **{
                        "instrumentation_scope.name": "meter_name",
                        "instrumentation_scope.version": "meter_version",
                        "instrumentation_scope.schema_url": "meter_schema_vrl",
                    }
                )
            )
        )

    def test_view_name(self):
        with self.assertRaises(Exception):
            View(name="name", instrument_name="instrument_name*")
