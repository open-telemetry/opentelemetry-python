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
from unittest.mock import Mock

from opentelemetry.sdk._metrics.view import View


class TestView(TestCase):
    def test_required_instrument_criteria(self):

        with self.assertRaises(Exception):
            View()

    def test_instrument_criteria(self):

        view = View(instrument_name="instrument_name")

        mock_instrument = Mock()
        mock_instrument.configure_mock(**{"name": "instrument_name"})

        self.assertTrue(view._matches_instrument(mock_instrument))
        self.assertTrue(view._matches_instrument(mock_instrument))
