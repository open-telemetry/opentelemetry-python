# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Loading and evaluation of a scenario's ``scenario.yaml``."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from opentelemetry.proto.metrics.v1.metrics_pb2 import Metric
from opentelemetry.test._otlp_test_server import (
    OtlpProtoTestServer,
    RecordedLogRecord,
    RecordedMetric,
    RecordedSpan,
)

from ._expect import Expectation, ExpectationFailure, build_span_index, parse_expectation, require_metric_field

_SCHEMA_FILE = Path(__file__).parent / "scenario.schema.json"
_DEFAULT_TIMEOUT = 30.0


@dataclass
class Received:
    """Telemetry accumulated from the sink over a scenario run, along with the app's state."""

    spans: list[RecordedSpan] = field(default_factory=list)
    metrics: list[RecordedMetric] = field(default_factory=list)
    logs: list[RecordedLogRecord] = field(default_factory=list)
    # Whether the app has exited cleanly on its own.
    exited: bool = False
    # The app's output, captured once it has stopped.
    stdout: str = ""
    stderr: str = ""

    def drain(self, sink: OtlpProtoTestServer) -> int:
        """Collect what the sink received since the last drain and return how many items that was."""
        spans = sink.drain_spans()
        metrics = sink.drain_metrics()
        logs = sink.drain_log_records()
        self.spans.extend(spans)
        self.metrics.extend(metrics)
        self.logs.extend(logs)
        return len(spans) + len(metrics) + len(logs)


@dataclass(frozen=True)
class SpansCondition:
    min_count: int = 1
    name: str | None = None

    def _get_count(self, received: Received) -> int:
        return sum(1 for recorded in received.spans if self.name is None or recorded.span.name == self.name)

    def satisfied(self, received: Received) -> bool:
        return self._get_count(received) >= self.min_count

    def progress(self, received: Received) -> str:
        return f"spans(name={self.name!r}): {self._get_count(received)}/{self.min_count}"


@dataclass(frozen=True)
class MetricCondition:
    name: str
    min: float
    field: str = "value"

    def _get_field_values(self, metric: Metric) -> list[float]:
        require_metric_field(metric, self.field)
        data_points = getattr(metric, metric.WhichOneof("data")).data_points
        if self.field == "value":
            return [getattr(point, point.WhichOneof("value")) for point in data_points if point.WhichOneof("value")]
        return [getattr(point, self.field) for point in data_points]

    def _get_max(self, received: Received) -> float | None:
        values = (
            value
            for recorded in received.metrics
            if recorded.metric.name == self.name
            for value in self._get_field_values(recorded.metric)
        )
        return max(values, default=None)

    def satisfied(self, received: Received) -> bool:
        highest = self._get_max(received)
        return highest is not None and highest >= self.min

    def progress(self, received: Received) -> str:
        return f"metric(name={self.name!r}, field={self.field!r}): max {self._get_max(received)} (need >= {self.min})"


@dataclass(frozen=True)
class LogsCondition:
    min_count: int = 1
    body_pattern: re.Pattern[str] | None = None

    def _matches(self, recorded: RecordedLogRecord) -> bool:
        if self.body_pattern is None:
            return True
        body = recorded.log_record.body
        return body.WhichOneof("value") == "string_value" and self.body_pattern.search(body.string_value) is not None

    def _get_count(self, received: Received) -> int:
        return sum(1 for recorded in received.logs if self._matches(recorded))

    def satisfied(self, received: Received) -> bool:
        return self._get_count(received) >= self.min_count

    def progress(self, received: Received) -> str:
        pattern = self.body_pattern.pattern if self.body_pattern is not None else None
        return f"logs(body_pattern={pattern!r}): {self._get_count(received)}/{self.min_count}"


@dataclass(frozen=True)
class ExitedCondition:
    def satisfied(self, received: Received) -> bool:
        return received.exited

    def progress(self, received: Received) -> str:
        return f"exited: {received.exited}"


Condition = SpansCondition | MetricCondition | LogsCondition | ExitedCondition


@dataclass(frozen=True)
class Scenario:
    description: str
    timeout: float
    until: list[Condition]
    expect: list[Expectation] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)

    def unmet(self, received: Received) -> list[Condition]:
        return [condition for condition in self.until if not condition.satisfied(received)]

    def failed_expectations(self, received: Received) -> list[ExpectationFailure]:
        """Return a failure for each ``expect`` entry the received telemetry doesn't satisfy."""
        spans = build_span_index(received.spans)
        return [failure for expectation in self.expect if (failure := expectation.failure(received, spans)) is not None]


@cache
def _get_schema() -> dict[str, Any]:
    with open(_SCHEMA_FILE, encoding="utf-8") as schema_file:
        return json.load(schema_file)


def _parse_condition(item: dict[str, Any]) -> Condition:
    if (spans := item.get("spans")) is not None:
        return SpansCondition(**spans)
    if (metric := item.get("metric")) is not None:
        return MetricCondition(**metric)
    if "exited" in item:
        return ExitedCondition()
    logs = item["logs"]
    pattern = logs.get("body_pattern")
    return LogsCondition(
        min_count=logs.get("min_count", 1),
        body_pattern=re.compile(pattern) if pattern is not None else None,
    )


def parse_scenario(document: Any) -> Scenario:
    """Validate a loaded ``scenario.yaml`` document and build a :class:`Scenario`."""
    jsonschema.validate(document, _get_schema())
    return Scenario(
        description=document["description"],
        timeout=float(document.get("timeout", _DEFAULT_TIMEOUT)),
        until=[_parse_condition(item) for item in document["until"]],
        expect=[parse_expectation(item) for item in document.get("expect", [])],
        env=document.get("env", {}),
    )


def load_scenario(path: Path) -> Scenario:
    with open(path, encoding="utf-8") as scenario_file:
        return parse_scenario(yaml.safe_load(scenario_file))
