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
from sys import version_info
from unittest import TestCase
from unittest.mock import Mock, patch

from opentelemetry.util import _providers


class Test_Providers(TestCase):

    # FIXME Remove when support for 3.7 is dropped.
    if version_info.minor == 7:
        entry_points_path = "importlib_metadata.entry_points"
    else:
        entry_points_path = "importlib.metadata.entry_points"

    @patch.dict(
        environ,
        {  # type: ignore
            "provider_environment_variable": "mock_provider_environment_variable"
        },
    )
    @patch(entry_points_path)
    def test__providers(self, mock_entry_points):

        reload(_providers)

        # FIXME Remove when support for 3.7 is dropped.
        if version_info.minor == 7:

            mock_a = Mock()
            mock_a.configure_mock(
                **{
                    "name": "mock_provider_environment_variable",
                    "group": "opentelemetry_provider",
                    "load.return_value": Mock(**{"return_value": "a"}),
                }
            )

            mock_entry_points.configure_mock(**{"return_value": (mock_a,)})

        # FIXME Remove when support for 3.9 is dropped.
        elif version_info.minor <= 9:

            mock_a = Mock()
            mock_a.configure_mock(
                **{
                    "name": "mock_provider_environment_variable",
                    "group": "opentelemetry_provider",
                    "load.return_value": Mock(**{"return_value": "a"}),
                }
            )

            mock_entry_points.configure_mock(
                **{"return_value": {"opentelemetry_provider": [mock_a]}}
            )

        else:

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
            _providers._load_provider(
                "provider_environment_variable", "provider"
            ),
            "a",
        )
