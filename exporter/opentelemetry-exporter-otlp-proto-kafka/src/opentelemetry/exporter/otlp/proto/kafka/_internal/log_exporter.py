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

import logging
from os import environ
from typing import Final, Mapping, Optional, Sequence

from kafka import KafkaProducer
from kafka.errors import KafkaError
from opentelemetry.exporter.otlp.proto.common._log_encoder import encode_logs
from opentelemetry.exporter.otlp.proto.kafka._internal.common import (
    DEFAULT_BROKERS,
    DEFAULT_CLIENT_ID,
    flush_producer,
    headers_from_env,
    publish_serialized_data,
    timeout_from_env,
)
from opentelemetry.sdk._logs import ReadableLogRecord
from opentelemetry.sdk._logs.export import (
    LogRecordExporter,
    LogRecordExportResult,
)
from opentelemetry.sdk._shared_internal import DuplicateFilter
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_KAFKA_BROKERS,
    OTEL_EXPORTER_KAFKA_CLIENT_ID,
    OTEL_EXPORTER_KAFKA_LOGS_TOPIC,
    OTEL_EXPORTER_OTLP_LOGS_HEADERS,
    OTEL_EXPORTER_OTLP_LOGS_TIMEOUT,
)

logger = logging.getLogger(__name__)
# This prevents logs generated when a log fails to be written to generate another log which fails to be written etc. etc.
logger.addFilter(DuplicateFilter())


DEFAULT_TOPIC: Final[str] = "otlp_logs"


class OTLPLogExporter(LogRecordExporter):
    def __init__(
        self,
        brokers: Optional[str] = None,
        client_id: Optional[str] = None,
        topic: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        producer: Optional[KafkaProducer] = None,
    ):
        self._brokers = brokers or environ.get(
            OTEL_EXPORTER_KAFKA_BROKERS, DEFAULT_BROKERS
        )
        self._client_id = client_id or environ.get(
            OTEL_EXPORTER_KAFKA_CLIENT_ID, DEFAULT_CLIENT_ID
        )
        self._topic = topic or environ.get(
            OTEL_EXPORTER_KAFKA_LOGS_TOPIC, DEFAULT_TOPIC
        )
        self._headers = headers_from_env(
            OTEL_EXPORTER_OTLP_LOGS_HEADERS, headers
        )
        self._timeout = timeout_from_env(
            OTEL_EXPORTER_OTLP_LOGS_TIMEOUT, timeout
        )

        self._producer = producer or KafkaProducer(
            bootstrap_servers=self._brokers,
            client_id=self._client_id,
        )

        self._shutdown = False

    def export(
        self, batch: Sequence[ReadableLogRecord]
    ) -> LogRecordExportResult:
        if self._shutdown:
            logger.warning("Exporter already shutdown, ignoring batch")
            return LogRecordExportResult.FAILURE

        serialized_data = encode_logs(batch).SerializeToString()
        try:
            publish_serialized_data(
                self._producer,
                self._topic,
                serialized_data,
                self._headers,
                self._timeout,
            )
            return LogRecordExportResult.SUCCESS
        except KafkaError as e:
            logger.error(
                "Failed to export logs batch reason: %s",
                e,
            )
            return LogRecordExportResult.FAILURE

    def shutdown(self):
        if self._shutdown:
            logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        self._producer.close()

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return flush_producer(self._producer, timeout_millis)
