from unittest.mock import Mock

import pytest

from opentelemetry.context import Context
from opentelemetry.metrics import Instrument
from opentelemetry.sdk.metrics._internal.measurement import (
    Measurement,
)
from opentelemetry.util.types import Attributes


@pytest.fixture
def attributes() -> Attributes:
    return {
        "key": "value",
    }


@pytest.fixture
def unix_time() -> int:
    return 1761568368250037000


@pytest.fixture
def context() -> Context:
    return Context()


@pytest.fixture
def instrument():
    return Mock(spec=Instrument)


@pytest.fixture
def measurement(
    unix_time: int,
    instrument: Instrument,
    context: Context,
    attributes: Attributes,
) -> Measurement:
    return Measurement(
        value=1.0,
        time_unix_nano=unix_time,
        instrument=instrument,
        context=context,
        attributes=attributes,
    )


def test_measurement_attribute_is_a_different_object(
    measurement: Measurement,
    attributes: Attributes,
):
    assert measurement.attributes is not attributes


def test_measurement_attribute_uneffected_by_change(
    measurement: Measurement,
    attributes: Attributes,
) -> None:
    attributes["new_key"] = "new_value"

    assert measurement.attributes == {
        "key": "value",
    }
