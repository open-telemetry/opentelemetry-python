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

from unittest.mock import Mock, patch
from unittest import TestCase
from logging import WARNING

from pytest import fixture

from opentelemetry.environment_variables import OTEL_PYTHON_METER_PROVIDER
from opentelemetry import metrics
from opentelemetry.metrics import (
    set_meter_provider,
    get_meter_provider,
    ProxyMeterProvider,
    _DefaultMeterProvider,
    _DefaultMeter
)


@fixture
def reset_meter_provider():
    original_meter_provider_value = metrics._METER_PROVIDER

    yield

    metrics._METER_PROVIDER = original_meter_provider_value


def test_set_meter_provider(reset_meter_provider):
    """
    Test that the API provides a way to set a global default MeterProvider
    """

    mock = Mock()

    assert metrics._METER_PROVIDER is None

    set_meter_provider(mock)

    assert metrics._METER_PROVIDER is mock


def test_get_meter_provider(reset_meter_provider):
    """
    Test that the API provides a way to get a global default MeterProvider
    """

    assert metrics._METER_PROVIDER is None

    assert isinstance(get_meter_provider(), ProxyMeterProvider)

    metrics._METER_PROVIDER = None

    with patch.dict(
        "os.environ", {OTEL_PYTHON_METER_PROVIDER: "test_meter_provider"}
    ):

        with patch("opentelemetry.metrics._load_provider", Mock()):
            with patch(
                "opentelemetry.metrics.cast",
                Mock(**{"return_value": "test_meter_provider"})
            ):
                assert get_meter_provider() == "test_meter_provider"


class TestGetMeter(TestCase):

    def test_get_meter_parameters(self):
        """
        Test that get_meter accepts name, version and schema_url
        """
        try:
            _DefaultMeterProvider().get_meter(
                "name", version="version", schema_url="schema_url"
            )
        except Exception as error:
            self.fail(f"Unexpected exception raised: {error}")

    def test_invalid_name(self):
        """
        Test that when an invalid name is specified a working meter
        implementation is returned as a fallback.
        """
        with self.assertLogs(level=WARNING):
            self.assertTrue(
                isinstance(
                    _DefaultMeterProvider().get_meter(""),
                    _DefaultMeter
                )
            )
        with self.assertLogs(level=WARNING):
            self.assertTrue(
                isinstance(
                    _DefaultMeterProvider().get_meter(None),
                    _DefaultMeter
                )
            )
