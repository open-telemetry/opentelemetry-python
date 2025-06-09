import pytest

from opentelemetry.sdk.metrics import Meter, MeterProvider
from opentelemetry.sdk.metrics.export import (
    InMemoryMetricReader,
)
from opentelemetry.util.types import Attributes


@pytest.fixture
def attributes() -> Attributes:
    return {
        "key": "value",
    }


@pytest.fixture
def meter_name() -> str:
    return "test_meter"


@pytest.fixture
def reader() -> InMemoryMetricReader:
    return InMemoryMetricReader()


@pytest.fixture
def meter_provider(reader: InMemoryMetricReader) -> MeterProvider:
    return MeterProvider(metric_readers=[reader])


@pytest.fixture
def meter(meter_provider: MeterProvider, meter_name: str) -> Meter:
    return meter_provider.get_meter("test_meter")


def test_measurement_collection(
    reader: InMemoryMetricReader,
    meter: Meter,
    attributes: Attributes,
) -> None:
    """
    Validate that adjusting attributes after a data point is created does not affect
    the already collected measurement.
    """
    counter = meter.create_counter("test_counter")
    counter.add(1, attributes)
    attributes["key"] = "new_value"
    counter.add(1, attributes)

    reader.collect()

    metrics_data = reader.get_metrics_data()
    resource_metric, *_ = metrics_data.resource_metrics
    scope_metric, *_ = resource_metric.scope_metrics
    metrics, *_ = scope_metric.metrics
    data = metrics.data
    data_point_1, data_point_2 = data.data_points

    assert data_point_1.attributes == {"key": "value"}
    assert data_point_2.attributes == {"key": "new_value"}
