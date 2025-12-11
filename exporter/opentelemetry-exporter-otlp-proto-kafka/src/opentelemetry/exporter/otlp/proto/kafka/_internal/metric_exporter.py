# Copyright The OpenTelemetry Authors
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
from __future__ import annotations

import logging
from os import environ
from typing import (
    Final,
    Optional,
)

from kafka import KafkaProducer
from kafka.errors import KafkaError
from opentelemetry.exporter.otlp.proto.common._internal.metrics_encoder import (
    OTLPMetricExporterMixin,
)
from opentelemetry.exporter.otlp.proto.common.metrics_encoder import (
    encode_metrics,
)
from opentelemetry.exporter.otlp.proto.kafka._internal.common import (
    DEFAULT_BROKERS,
    DEFAULT_CLIENT_ID,
    flush_producer,
    headers_from_env,
    publish_serialized_data,
    timeout_from_env,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_KAFKA_BROKERS,
    OTEL_EXPORTER_KAFKA_CLIENT_ID,
    OTEL_EXPORTER_KAFKA_METRICS_TOPIC,
    OTEL_EXPORTER_OTLP_METRICS_HEADERS,
    OTEL_EXPORTER_OTLP_METRICS_TIMEOUT,
)
from opentelemetry.sdk.metrics._internal.aggregation import Aggregation
from opentelemetry.sdk.metrics.export import (
    AggregationTemporality,
    MetricExporter,
    MetricExportResult,
    MetricsData,
)

logger = logging.getLogger(__name__)


DEFAULT_TOPIC: Final[str] = "otlp_metrics"


class OTLPMetricExporter(MetricExporter, OTLPMetricExporterMixin):
    def __init__(
        self,
        brokers: str | None = None,
        client_id: str | None = None,
        topic: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        preferred_temporality: dict[type, AggregationTemporality]
        | None = None,
        preferred_aggregation: dict[type, Aggregation] | None = None,
        producer: Optional[KafkaProducer] = None,
    ):
        self._brokers = brokers or environ.get(
            OTEL_EXPORTER_KAFKA_BROKERS, DEFAULT_BROKERS
        )
        self._client_id = client_id or environ.get(
            OTEL_EXPORTER_KAFKA_CLIENT_ID, DEFAULT_CLIENT_ID
        )
        self._topic = topic or environ.get(
            OTEL_EXPORTER_KAFKA_METRICS_TOPIC, DEFAULT_TOPIC
        )
        self._headers = headers_from_env(
            OTEL_EXPORTER_OTLP_METRICS_HEADERS, headers
        )
        self._timeout = timeout_from_env(
            OTEL_EXPORTER_OTLP_METRICS_TIMEOUT, timeout
        )

        self._producer = producer or KafkaProducer(
            bootstrap_servers=self._brokers,
            client_id=self._client_id,
        )

        self._shutdown = False

        self._common_configuration(
            preferred_temporality, preferred_aggregation
        )
        self._shutdown = False

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: Optional[float] = 10000,
        **kwargs,
    ) -> MetricExportResult:
        if self._shutdown:
            logger.warning("Exporter already shutdown, ignoring batch")
            return MetricExportResult.FAILURE
        serialized_data = encode_metrics(metrics_data).SerializeToString()
        try:
            publish_serialized_data(
                self._producer,
                self._topic,
                serialized_data,
                self._headers,
                self._timeout,
            )
            return MetricExportResult.SUCCESS
        except KafkaError as e:
            logger.error(
                "Failed to export metrics batch reason: %s",
                e,
            )
            return MetricExportResult.FAILURE

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        if self._shutdown:
            logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._producer.close()

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return flush_producer(self._producer, timeout_millis)
