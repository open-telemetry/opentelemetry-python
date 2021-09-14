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

from unittest.mock import Mock

from pytest import fixture

from opentelemetry import metrics
from opentelemetry.metrics import (
    set_meter_provider, get_meter_provider, ProxyMeterProvider
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


def test_get_meter_provider():
    """
    Test that the API provides a way to get a global default MeterProvider
    """

    assert isinstance(get_meter_provider(), ProxyMeterProvider)
