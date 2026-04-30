from collections import Counter

from opentelemetry.metrics import MeterProvider
from opentelemetry.sdk.environment_variables import (
    OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED,
)
from opentelemetry.sdk.environment_variables._internal import (
    parse_boolean_environment_variable,
)
from opentelemetry.semconv._incubating.attributes.otel_attributes import (
    OTEL_COMPONENT_NAME,
    OTEL_COMPONENT_TYPE,
)
from opentelemetry.semconv._incubating.metrics.otel_metrics import (
    create_otel_sdk_metric_reader_collection_duration,
)

_component_counter = Counter()


class MetricReaderMetrics:
    def __init__(
        self, component_type: str, meter_provider: MeterProvider
    ) -> None:
        meter = meter_provider.get_meter("opentelemetry-sdk")

        count = _component_counter[component_type]
        _component_counter[component_type] = count + 1

        self._standard_attrs = {
            OTEL_COMPONENT_TYPE: component_type,
            OTEL_COMPONENT_NAME: f"{component_type}/{count}",
        }

        self._collection_duration = (
            create_otel_sdk_metric_reader_collection_duration(meter)
        )
        self._disabled = not parse_boolean_environment_variable(
            OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED
        )

    def record_collection(self, duration: float) -> None:
        if self._disabled:
            return
        self._collection_duration.record(duration, self._standard_attrs)
