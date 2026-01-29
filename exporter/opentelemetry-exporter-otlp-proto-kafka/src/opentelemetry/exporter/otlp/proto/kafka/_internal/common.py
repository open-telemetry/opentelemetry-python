from os import environ
from typing import Final, Mapping, Optional, Sequence, Tuple

from kafka import KafkaProducer
from kafka.errors import KafkaTimeoutError
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TIMEOUT,
)
from opentelemetry.util.re import parse_env_headers

DEFAULT_TIMEOUT: Final[int] = 10
DEFAULT_CLIENT_ID: Final[str] = "otel-exporter"
DEFAULT_BROKERS: Final[str] = "localhost:9092"


def publish_serialized_data(
    producer: KafkaProducer,
    topic: str,
    serialized_data: bytes,
    headers: Sequence[tuple[str, bytes]],
    timeout: float,
) -> None:
    future = producer.send(
        topic,
        value=serialized_data,
        headers=headers,
    )
    future.get(timeout)


def flush_producer(producer: KafkaProducer, timeout_millis: float) -> bool:
    try:
        producer.flush(timeout_millis / 1000)
        return True
    except KafkaTimeoutError:
        return False


def timeout_from_env(
    exporter_environment_variable_name: str, timeout: Optional[float]
) -> float:
    return timeout or float(
        environ.get(
            exporter_environment_variable_name,
            environ.get(OTEL_EXPORTER_OTLP_TIMEOUT, DEFAULT_TIMEOUT),
        )
    )


def headers_from_env(
    exporter_environment_variable_name: str,
    headers: Optional[Mapping[str, str]],
) -> Sequence[Tuple[str, bytes]]:
    headers_string = environ.get(
        exporter_environment_variable_name,
        environ.get(OTEL_EXPORTER_OTLP_HEADERS, ""),
    )
    mapping_headers = headers or parse_env_headers(
        headers_string, liberal=True
    )
    return [(key, value.encode()) for key, value in mapping_headers.items()]
