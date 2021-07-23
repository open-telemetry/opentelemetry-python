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
# type: ignore

from unittest import TestCase
from unittest.mock import Mock, patch

from opentelemetry.configurator import _configure


class TestConfigurator(TestCase):
    @patch("opentelemetry.configurator.iter_entry_points")
    @patch.dict(
        "opentelemetry.configurator.environ",
        {"OTEL_PYTHON_CONFIGURATORS": "configurator_0"},
    )
    def test_configure(self, mock_iter_entry_points):

        mock_configurator_0_entry_point = Mock()
        # This is not done in the previous call to `Mock` because `name` is a
        # reserved attribute that has to be overriden like this.
        mock_configurator_0_entry_point.name = "configurator_0"

        mock_iter_entry_points.configure_mock(
            **{"return_value": [mock_configurator_0_entry_point]}
        )

        _configure()

        self.assertIsNone(
            mock_configurator_0_entry_point.load()().configure.assert_called()
        )
