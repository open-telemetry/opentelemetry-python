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

from importlib import reload
from os import environ
from unittest import TestCase
from unittest.mock import Mock, patch

from opentelemetry.util import _providers


class Test_Providers(TestCase):  # pylint: disable=invalid-name
    @patch.dict(
        environ,
        {  # type: ignore
            "provider_environment_variable": "mock_provider_environment_variable"
        },
    )
    @patch("opentelemetry.util._importlib_metadata.entry_points")
    def test__providers(self, mock_entry_points):

        reload(_providers)

        mock_entry_points.configure_mock(
            **{
                "side_effect": [
                    [
                        Mock(
                            **{
                                "load.return_value": Mock(
                                    **{"return_value": "a"}
                                )
                            }
                        ),
                    ],
                ]
            }
        )

        self.assertEqual(
            _providers._load_provider(  # pylint: disable=protected-access
                "provider_environment_variable", "provider"
            ),
            "a",
        )
