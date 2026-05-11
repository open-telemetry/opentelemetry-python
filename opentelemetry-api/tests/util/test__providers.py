# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

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
