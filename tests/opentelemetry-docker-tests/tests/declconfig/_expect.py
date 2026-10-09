# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Matchers for a scenario's ``expect`` entries, checked against the received telemetry."""

from __future__ import annotations

import operator
import re
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Generic, TypeVar

import yaml

from opentelemetry.proto.common.v1.common_pb2 import AnyValue, InstrumentationScope, KeyValue
from opentelemetry.proto.logs.v1.logs_pb2 import SeverityNumber
from opentelemetry.proto.metrics.v1.metrics_pb2 import AggregationTemporality, Metric
from opentelemetry.proto.trace.v1.trace_pb2 import Span, Status
from opentelemetry.test._otlp_test_server import RecordedLogRecord, RecordedMetric, RecordedSpan

if TYPE_CHECKING:
    from ._scenario import Received

# Metric data types that each metric or data point field applies to.
FIELD_DATA_TYPES = {
    "temporality": ("sum", "histogram", "exponential_histogram"),
    "monotonic": ("sum",),
    "value": ("gauge", "sum"),
    "count": ("histogram", "exponential_histogram", "summary"),
    "sum": ("histogram", "exponential_histogram", "summary"),
    "min": ("histogram", "exponential_histogram"),
    "max": ("histogram", "exponential_histogram"),
    "explicit_bounds": ("histogram",),
    "bucket_counts": ("histogram",),
}

# Closest (or unexpected) candidates listed in a failure message.
_MAX_CANDIDATES = 3

_TYPED_KEYS = frozenset({"string", "bool", "int", "double", "kvlist"})
_COMPARISONS: dict[str, Callable[[Any, Any], bool]] = {
    "gt": operator.gt,
    "gte": operator.ge,
    "lt": operator.lt,
    "lte": operator.le,
}

# Received spans by ``(trace_id, span_id)``, for resolving parents, links and log correlation.
SpanIndex = dict[tuple[bytes, bytes], RecordedSpan]

_T = TypeVar("_T")


def build_span_index(spans: Iterable[RecordedSpan]) -> SpanIndex:
    return {(recorded.span.trace_id, recorded.span.span_id): recorded for recorded in spans}


def require_metric_field(metric: Metric, field_name: str) -> None:
    data_type = metric.WhichOneof("data")
    if data_type not in FIELD_DATA_TYPES[field_name]:
        raise ValueError(f"Metric {metric.name!r} is a {data_type}, field {field_name!r} does not apply to it")


# Values are compared and described as plain Python values: str, bool, int, float, bytes,
# list for arrays and dict for kvlists. ``None`` stands for an absent value.
def _any_value_to_python(value: AnyValue) -> Any:
    kind = value.WhichOneof("value")
    if kind is None:
        return None
    if kind == "array_value":
        return [_any_value_to_python(item) for item in value.array_value.values]
    if kind == "kvlist_value":
        return _key_values_to_python(value.kvlist_value.values)
    return getattr(value, kind)


def _key_values_to_python(key_values: Iterable[KeyValue]) -> dict[str, Any]:
    return {kv.key: _any_value_to_python(kv.value) for kv in key_values}


def _literal_to_python(literal: Any) -> Any:
    """Resolve the typed literals of a scenario value, such as ``{double: 5}``, to plain values."""
    if isinstance(literal, dict):
        ((kind, payload),) = literal.items()
        if kind == "kvlist":
            return {key: _literal_to_python(value) for key, value in payload.items()}
        return float(payload) if kind == "double" else payload
    if isinstance(literal, list):
        return [_literal_to_python(item) for item in literal]
    return literal


def _is_numeric_value(value: Any) -> bool:
    # bool is a subclass of int, but not a number here.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _values_equal(expected: Any, actual: Any, strict: bool) -> bool:
    """Compare values including their types, so ``5``, ``5.0``, ``"5"`` and ``True`` all differ.

    With ``strict=False``, numbers compare by value regardless of int or double.
    """
    if not strict and _is_numeric_value(expected) and _is_numeric_value(actual):
        return expected == actual
    if type(expected) is not type(actual):
        return False
    if isinstance(expected, list):
        return len(expected) == len(actual) and all(
            _values_equal(item, other, strict) for item, other in zip(expected, actual)
        )
    if isinstance(expected, dict):
        return expected.keys() == actual.keys() and all(
            _values_equal(value, actual[key], strict) for key, value in expected.items()
        )
    return expected == actual


def _to_flow_yaml(value: Any) -> str:
    dumped = yaml.safe_dump(value, default_flow_style=True, sort_keys=False, width=1000, allow_unicode=True)
    # A plain scalar document ends with an explicit "..." marker.
    return dumped.removesuffix("\n...\n").strip()


def _describe_value(value: Any) -> str:
    return "<absent>" if value is None else _to_flow_yaml(value)


@dataclass(frozen=True)
class Mismatch:
    """How one field of a received item fails its matcher."""

    path: tuple[str, ...]
    expected: str
    actual: str

    def nested(self, prefix: str) -> Mismatch:
        return replace(self, path=(prefix, *self.path))

    def __str__(self) -> str:
        # Index segments such as "['service.name']" attach without a dot.
        path = "".join(segment if segment.startswith("[") else f".{segment}" for segment in self.path)
        return f"{path.removeprefix('.')}: expected {self.expected}, got {self.actual}"


def _nest_mismatches(prefix: str, mismatches: Iterable[Mismatch]) -> Iterator[Mismatch]:
    return (mismatch.nested(prefix) for mismatch in mismatches)


@dataclass(frozen=True)
class ValueMatcher:
    """A literal (``equals``) or operators that must all hold, applied to one value.

    Without any of them, it matches anything, including an absent value.
    """

    equals: Any = None
    pattern: re.Pattern[str] | None = None
    exists: bool | None = None
    bounds: tuple[tuple[str, float], ...] = ()

    def describe(self) -> str:
        if self.equals is not None:
            return _describe_value(self.equals)
        parts = []
        if self.exists is not None:
            parts.append("present" if self.exists else "<absent>")
        if self.pattern is not None:
            parts.append(f"match for {self.pattern.pattern!r}")
        parts.extend(f"{name} {bound}" for name, bound in self.bounds)
        return " and ".join(parts)

    def check(self, label: str, actual: Any, strict: bool = True) -> Iterator[Mismatch]:
        """Yield how ``actual`` fails this matcher, prefixed with ``label``.

        With ``strict=False``, numeric literals match int and double values alike.
        """
        if self == _ANY_VALUE:
            return
        if (actual is None) != (self.exists is False) or not self._holds(actual, strict):
            yield Mismatch((label,), self.describe(), _describe_value(actual))

    def _holds(self, actual: Any, strict: bool) -> bool:
        if actual is None:
            return True
        if self.equals is not None and not _values_equal(self.equals, actual, strict):
            return False
        if self.pattern is not None and (not isinstance(actual, str) or self.pattern.search(actual) is None):
            return False
        return all(_is_numeric_value(actual) and _COMPARISONS[name](actual, bound) for name, bound in self.bounds)


_ANY_VALUE = ValueMatcher()


def parse_value_matcher(spec: Any) -> ValueMatcher:
    """Build a matcher from a ``value_matcher``, ``string_matcher`` or ``number_matcher``."""
    if not isinstance(spec, dict) or spec.keys() <= _TYPED_KEYS:
        return ValueMatcher(equals=_literal_to_python(spec))
    pattern = spec.get("pattern")
    return ValueMatcher(
        pattern=re.compile(pattern) if pattern is not None else None,
        exists=spec.get("exists"),
        bounds=tuple((name, spec[name]) for name in _COMPARISONS if name in spec),
    )


@dataclass(frozen=True)
class LiteralMatcher(Generic[_T]):
    """An exact, untagged value such as an enum name or a bool. Unset, it matches anything."""

    expected: _T | None = None

    def check(self, label: str, actual: Any) -> Iterator[Mismatch]:
        if self.expected is not None and self.expected != actual:
            yield Mismatch((label,), str(self.expected), str(actual))


@dataclass(frozen=True)
class AttributesMatcher:
    matchers: dict[str, ValueMatcher] = field(default_factory=dict)
    strict: bool = False

    def check(self, label: str, attributes: Sequence[KeyValue]) -> Iterator[Mismatch]:
        actual = _key_values_to_python(attributes)
        for key, matcher in self.matchers.items():
            yield from _nest_mismatches(label, matcher.check(f"[{key!r}]", actual.get(key)))
        if self.strict and (unexpected := sorted(actual.keys() - self.matchers.keys())):
            yield Mismatch((label,), "no unlisted keys", ", ".join(unexpected))


@dataclass(frozen=True)
class ScopeMatcher:
    name: ValueMatcher = ValueMatcher()
    version: ValueMatcher = ValueMatcher()
    attributes: AttributesMatcher = AttributesMatcher()

    def check(self, scope: InstrumentationScope) -> Iterator[Mismatch]:
        yield from self.name.check("name", scope.name or None)
        yield from self.version.check("version", scope.version or None)
        yield from self.attributes.check("attributes", scope.attributes)


@dataclass(frozen=True)
class LinkMatcher:
    trace_state: ValueMatcher = ValueMatcher()
    span: SpanMatcher | None = None
    attributes: AttributesMatcher = AttributesMatcher()

    def check(self, link: Span.Link, spans: SpanIndex) -> Iterator[Mismatch]:
        yield from self.trace_state.check("trace_state", link.trace_state or None)
        if self.span is not None:
            yield from self.span.check_reference("span", spans, link.trace_id, link.span_id)
        yield from self.attributes.check("attributes", link.attributes)


@dataclass(frozen=True)
class SpanMatcher:
    name: ValueMatcher = ValueMatcher()
    kind: LiteralMatcher[str] = LiteralMatcher()
    status_code: LiteralMatcher[str] = LiteralMatcher()
    status_message: ValueMatcher = ValueMatcher()
    trace_state: ValueMatcher = ValueMatcher()
    root: LiteralMatcher[bool] = LiteralMatcher()
    parent: SpanMatcher | None = None
    links: tuple[LinkMatcher, ...] = ()
    link_count: ValueMatcher = ValueMatcher()
    scope: ScopeMatcher | None = None
    attributes: AttributesMatcher = AttributesMatcher()

    def check(self, recorded: RecordedSpan, spans: SpanIndex) -> Iterator[Mismatch]:
        span = recorded.span
        yield from self.name.check("name", span.name or None)
        yield from self.kind.check("kind", Span.SpanKind.Name(span.kind).removeprefix("SPAN_KIND_"))
        status_code = Status.StatusCode.Name(span.status.code).removeprefix("STATUS_CODE_")
        yield from _nest_mismatches("status", self.status_code.check("code", status_code))
        yield from _nest_mismatches("status", self.status_message.check("message", span.status.message or None))
        yield from self.trace_state.check("trace_state", span.trace_state or None)
        yield from self.root.check("root", not span.parent_span_id)
        if self.parent is not None:
            yield from self.parent.check_reference("parent", spans, span.trace_id, span.parent_span_id)
        for position, link_matcher in enumerate(self.links):
            label = f"links[{position}]"
            candidates = [list(link_matcher.check(link, spans)) for link in span.links]
            if not candidates:
                yield Mismatch((label,), "a link", "<absent>")
            elif all(candidates):
                yield from _nest_mismatches(label, min(candidates, key=len))
        yield from self.link_count.check("link_count", len(span.links), strict=False)
        if self.scope is not None:
            yield from _nest_mismatches("scope", self.scope.check(recorded.scope))
        yield from self.attributes.check("attributes", span.attributes)

    def check_reference(self, label: str, spans: SpanIndex, trace_id: bytes, span_id: bytes) -> Iterator[Mismatch]:
        """Match the received span with the given IDs, yielding its mismatches nested under ``label``."""
        if not span_id:
            yield Mismatch((label,), "a span", "<absent>")
            return
        target = spans.get((trace_id, span_id))
        if target is None:
            yield Mismatch((label,), "a received span", span_id.hex())
            return
        yield from _nest_mismatches(label, self.check(target, spans))


def _get_optional_double(point: Any, field_name: str) -> float | None:
    try:
        present = point.HasField(field_name)
    except ValueError:
        # Not an optional field, so it is always present.
        present = True
    return getattr(point, field_name) if present else None


@dataclass(frozen=True)
class DataPointMatcher:
    value: ValueMatcher | None = None
    count: ValueMatcher | None = None
    sum: ValueMatcher | None = None
    min: ValueMatcher | None = None
    max: ValueMatcher | None = None
    explicit_bounds: LiteralMatcher[list[float]] | None = None
    bucket_counts: LiteralMatcher[list[int]] | None = None
    exemplar_count: ValueMatcher = ValueMatcher()
    attributes: AttributesMatcher = AttributesMatcher()

    def check(self, point: Any, metric: Metric) -> Iterator[Mismatch]:
        if self.value is not None:
            require_metric_field(metric, "value")
            kind = point.WhichOneof("value")
            actual = getattr(point, kind) if kind else None
            yield from self.value.check("value", actual)
        if self.count is not None:
            require_metric_field(metric, "count")
            yield from self.count.check("count", point.count, strict=False)
        for field_name in ("sum", "min", "max"):
            if (matcher := getattr(self, field_name)) is not None:
                require_metric_field(metric, field_name)
                yield from matcher.check(field_name, _get_optional_double(point, field_name), strict=False)
        for field_name in ("explicit_bounds", "bucket_counts"):
            if (literal := getattr(self, field_name)) is not None:
                require_metric_field(metric, field_name)
                yield from literal.check(field_name, list(getattr(point, field_name)))
        yield from self.exemplar_count.check("exemplar_count", len(point.exemplars), strict=False)
        yield from self.attributes.check("attributes", point.attributes)


@dataclass(frozen=True)
class MetricMatcher:
    name: ValueMatcher = ValueMatcher()
    type: LiteralMatcher[str] = LiteralMatcher()
    unit: ValueMatcher = ValueMatcher()
    description: ValueMatcher = ValueMatcher()
    temporality: LiteralMatcher[str] | None = None
    monotonic: LiteralMatcher[bool] | None = None
    scope: ScopeMatcher | None = None
    data_point: DataPointMatcher | None = None

    def check(self, recorded: RecordedMetric, point: Any) -> Iterator[Mismatch]:
        metric = recorded.metric
        data_type = metric.WhichOneof("data")
        identity = [*self.name.check("name", metric.name or None), *self.type.check("type", data_type)]
        yield from identity
        if identity:
            # A different metric: skip the fields that may not apply to its type.
            return
        yield from self.unit.check("unit", metric.unit or None)
        yield from self.description.check("description", metric.description or None)
        if self.temporality is not None:
            require_metric_field(metric, "temporality")
            temporality = AggregationTemporality.Name(getattr(metric, data_type).aggregation_temporality)
            yield from self.temporality.check("temporality", temporality.removeprefix("AGGREGATION_TEMPORALITY_"))
        if self.monotonic is not None:
            require_metric_field(metric, "monotonic")
            yield from self.monotonic.check("monotonic", metric.sum.is_monotonic)
        if self.scope is not None:
            yield from _nest_mismatches("scope", self.scope.check(recorded.scope))
        if self.data_point is not None:
            yield from _nest_mismatches("data_point", self.data_point.check(point, metric))


@dataclass(frozen=True)
class LogMatcher:
    body: ValueMatcher = ValueMatcher()
    severity_number: LiteralMatcher[str] = LiteralMatcher()
    severity_text: ValueMatcher = ValueMatcher()
    event_name: ValueMatcher = ValueMatcher()
    trace_context: LiteralMatcher[bool] = LiteralMatcher()
    span: SpanMatcher | None = None
    scope: ScopeMatcher | None = None
    attributes: AttributesMatcher = AttributesMatcher()

    def check(self, recorded: RecordedLogRecord, spans: SpanIndex) -> Iterator[Mismatch]:
        log_record = recorded.log_record
        yield from self.body.check("body", _any_value_to_python(log_record.body))
        severity_number = SeverityNumber.Name(log_record.severity_number).removeprefix("SEVERITY_NUMBER_")
        yield from self.severity_number.check("severity_number", severity_number)
        yield from self.severity_text.check("severity_text", log_record.severity_text or None)
        yield from self.event_name.check("event_name", log_record.event_name or None)
        ids_set = (bool(log_record.trace_id), bool(log_record.span_id))
        yield from self.trace_context.check("trace_context", ids_set[0] if ids_set[0] == ids_set[1] else "partial")
        if self.span is not None:
            yield from self.span.check_reference("span", spans, log_record.trace_id, log_record.span_id)
        if self.scope is not None:
            yield from _nest_mismatches("scope", self.scope.check(recorded.scope))
        yield from self.attributes.check("attributes", log_record.attributes)


@dataclass(frozen=True)
class Counts:
    count: int | None = None
    min_count: int | None = None
    max_count: int | None = None

    @property
    def lower(self) -> int:
        if self.count is not None:
            return self.count
        return self.min_count if self.min_count is not None else 1

    @property
    def upper(self) -> int | None:
        return self.count if self.count is not None else self.max_count

    def satisfied(self, matched: int) -> bool:
        return matched >= self.lower and (self.upper is None or matched <= self.upper)

    def __str__(self) -> str:
        if self.count is not None:
            return f"== {self.count}"
        if self.upper is None:
            return f">= {self.lower}"
        return f">= {self.lower} and <= {self.upper}"


@dataclass(frozen=True)
class ExpectationFailure:
    """An unmet ``expect`` entry: its source, a summary line, and indented detail lines."""

    key: str
    source: dict[str, Any]
    summary: str
    details: tuple[str, ...] = ()

    def __str__(self) -> str:
        header = _to_flow_yaml(self.source)
        return "\n".join([f"{self.key}: {header}", f"  {self.summary}", *(f"  {detail}" for detail in self.details)])


def _count_failure(
    key: str, source: dict[str, Any], counts: Counts, candidates: list[tuple[str, list[Mismatch]]], noun: str
) -> ExpectationFailure | None:
    """Report a counted expectation, given ``(label, mismatches)`` for every candidate item."""
    matched = [label for label, mismatches in candidates if not mismatches]
    if counts.satisfied(len(matched)):
        return None
    details: list[str] = []
    if not candidates:
        details.append(f"no {noun} received")
    elif len(matched) < counts.lower:
        unmatched = dict.fromkeys((label, tuple(mismatches)) for label, mismatches in candidates if mismatches)
        # Prefer candidates with the expected name, then those with the fewest mismatches.
        closest = sorted(
            unmatched,
            key=lambda item: (any(mismatch.path == ("name",) for mismatch in item[1]), len(item[1])),
        )
        details.extend(
            f"closest {label}: {'; '.join(map(str, mismatches))}" for label, mismatches in closest[:_MAX_CANDIDATES]
        )
    else:
        details.extend(f"matched {label}" for label in matched[:_MAX_CANDIDATES])
    return ExpectationFailure(key, source, f"matched {len(matched)}, expected {counts}", tuple(details))


@dataclass(frozen=True)
class SpansExpectation:
    matcher: SpanMatcher
    counts: Counts = Counts()
    source: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)

    def failure(self, received: Received, spans: SpanIndex) -> ExpectationFailure | None:
        candidates = [
            (repr(recorded.span.name), list(self.matcher.check(recorded, spans))) for recorded in received.spans
        ]
        return _count_failure("spans", self.source, self.counts, candidates, "spans")


def _get_data_points(metric: Metric) -> Sequence[Any]:
    data_type = metric.WhichOneof("data")
    return getattr(metric, data_type).data_points if data_type is not None else ()


@dataclass(frozen=True)
class MetricExpectation:
    matcher: MetricMatcher
    counts: Counts = Counts()
    source: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)

    def failure(self, received: Received, spans: SpanIndex) -> ExpectationFailure | None:
        candidates = [
            (
                f"{recorded.metric.name!r} {_describe_value(_key_values_to_python(point.attributes))}",
                list(self.matcher.check(recorded, point)),
            )
            for recorded in received.metrics
            for point in _get_data_points(recorded.metric)
        ]
        return _count_failure("metric", self.source, self.counts, candidates, "metric data points")


@dataclass(frozen=True)
class LogsExpectation:
    matcher: LogMatcher
    counts: Counts = Counts()
    source: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)

    def failure(self, received: Received, spans: SpanIndex) -> ExpectationFailure | None:
        candidates = [
            (
                f"body={_describe_value(_any_value_to_python(recorded.log_record.body))}",
                list(self.matcher.check(recorded, spans)),
            )
            for recorded in received.logs
        ]
        return _count_failure("logs", self.source, self.counts, candidates, "logs")


@dataclass(frozen=True)
class ResourceExpectation:
    attributes: AttributesMatcher = AttributesMatcher()
    schema_url: ValueMatcher = ValueMatcher()
    source: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)

    def failure(self, received: Received, spans: SpanIndex) -> ExpectationFailure | None:
        resources = [
            *(("span", recorded.resource, recorded.resource_schema_url) for recorded in received.spans),
            *(("metric", recorded.resource, recorded.resource_schema_url) for recorded in received.metrics),
            *(("log", recorded.resource, recorded.resource_schema_url) for recorded in received.logs),
        ]
        if not resources:
            return ExpectationFailure("resource", self.source, "nothing received")
        failing = 0
        # One example per distinct non-matching resource.
        examples: dict[tuple[bytes, str], tuple[str, list[Mismatch]]] = {}
        for signal, resource, schema_url in resources:
            mismatches = [
                *self.schema_url.check("schema_url", schema_url or None),
                *self.attributes.check("attributes", resource.attributes),
            ]
            if mismatches:
                failing += 1
                examples.setdefault((resource.SerializeToString(deterministic=True), schema_url), (signal, mismatches))
        if not failing:
            return None
        return ExpectationFailure(
            "resource",
            self.source,
            f"{failing} of {len(resources)} items have a non-matching resource",
            tuple(
                f"{signal}: {'; '.join(map(str, mismatches))}"
                for signal, mismatches in list(examples.values())[:_MAX_CANDIDATES]
            ),
        )


@dataclass(frozen=True)
class OutputExpectation:
    """A regex that must (or, with ``exists=False``, must not) be found in the app's stdout or stderr."""

    stream: str
    pattern: re.Pattern[str]
    exists: bool = True
    source: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)

    def failure(self, received: Received, spans: SpanIndex) -> ExpectationFailure | None:
        found = self.pattern.search(getattr(received, self.stream)) is not None
        if found == self.exists:
            return None
        summary = f"{self.stream} {'has no' if self.exists else 'has a'} match for {self.pattern.pattern!r}"
        return ExpectationFailure("output", self.source, summary)


Expectation = SpansExpectation | MetricExpectation | LogsExpectation | ResourceExpectation | OutputExpectation


def _parse_value(spec: dict[str, Any], key: str) -> ValueMatcher:
    return parse_value_matcher(spec[key]) if key in spec else ValueMatcher()


def _parse_optional(spec: dict[str, Any], key: str) -> ValueMatcher | None:
    return parse_value_matcher(spec[key]) if key in spec else None


def _parse_optional_literal(spec: dict[str, Any], key: str) -> LiteralMatcher[Any] | None:
    return LiteralMatcher(spec[key]) if key in spec else None


def _parse_attributes(spec: dict[str, Any]) -> AttributesMatcher:
    if (attributes := spec.get("attributes")) is None:
        return AttributesMatcher()
    return AttributesMatcher(
        matchers={key: parse_value_matcher(value) for key, value in attributes.get("values", {}).items()},
        strict=attributes.get("strict", False),
    )


def _parse_scope(spec: dict[str, Any]) -> ScopeMatcher | None:
    if "scope" not in spec:
        return None
    scope = spec["scope"]
    return ScopeMatcher(
        name=_parse_value(scope, "name"),
        version=_parse_value(scope, "version"),
        attributes=_parse_attributes(scope),
    )


def _parse_span_matcher(spec: dict[str, Any]) -> SpanMatcher:
    status = spec.get("status", {})
    return SpanMatcher(
        name=_parse_value(spec, "name"),
        kind=LiteralMatcher(spec.get("kind")),
        status_code=LiteralMatcher(status.get("code")),
        status_message=_parse_value(status, "message"),
        trace_state=_parse_value(spec, "trace_state"),
        root=LiteralMatcher(spec.get("root")),
        parent=_parse_span_matcher(spec["parent"]) if "parent" in spec else None,
        links=tuple(
            LinkMatcher(
                trace_state=_parse_value(link, "trace_state"),
                span=_parse_span_matcher(link["span"]) if "span" in link else None,
                attributes=_parse_attributes(link),
            )
            for link in spec.get("links", [])
        ),
        link_count=_parse_value(spec, "link_count"),
        scope=_parse_scope(spec),
        attributes=_parse_attributes(spec),
    )


def _parse_data_point_matcher(spec: dict[str, Any]) -> DataPointMatcher:
    return DataPointMatcher(
        value=_parse_optional(spec, "value"),
        count=_parse_optional(spec, "count"),
        sum=_parse_optional(spec, "sum"),
        min=_parse_optional(spec, "min"),
        max=_parse_optional(spec, "max"),
        explicit_bounds=_parse_optional_literal(spec, "explicit_bounds"),
        bucket_counts=_parse_optional_literal(spec, "bucket_counts"),
        exemplar_count=_parse_value(spec, "exemplar_count"),
        attributes=_parse_attributes(spec),
    )


def _parse_metric_matcher(spec: dict[str, Any]) -> MetricMatcher:
    return MetricMatcher(
        name=_parse_value(spec, "name"),
        type=LiteralMatcher(spec.get("type")),
        unit=_parse_value(spec, "unit"),
        description=_parse_value(spec, "description"),
        temporality=_parse_optional_literal(spec, "temporality"),
        monotonic=_parse_optional_literal(spec, "monotonic"),
        scope=_parse_scope(spec),
        data_point=_parse_data_point_matcher(spec["data_point"]) if "data_point" in spec else None,
    )


def _parse_log_matcher(spec: dict[str, Any]) -> LogMatcher:
    return LogMatcher(
        body=_parse_value(spec, "body"),
        severity_number=LiteralMatcher(spec.get("severity_number")),
        severity_text=_parse_value(spec, "severity_text"),
        event_name=_parse_value(spec, "event_name"),
        trace_context=LiteralMatcher(spec.get("trace_context")),
        span=_parse_span_matcher(spec["span"]) if "span" in spec else None,
        scope=_parse_scope(spec),
        attributes=_parse_attributes(spec),
    )


def _parse_counts(spec: dict[str, Any]) -> Counts:
    return Counts(count=spec.get("count"), min_count=spec.get("min_count"), max_count=spec.get("max_count"))


def parse_expectation(item: dict[str, Any]) -> Expectation:
    """Build an expectation from one schema-validated ``expect`` item."""
    if (spans := item.get("spans")) is not None:
        return SpansExpectation(matcher=_parse_span_matcher(spans), counts=_parse_counts(spans), source=spans)
    if (metric := item.get("metric")) is not None:
        return MetricExpectation(matcher=_parse_metric_matcher(metric), counts=_parse_counts(metric), source=metric)
    if (logs := item.get("logs")) is not None:
        return LogsExpectation(matcher=_parse_log_matcher(logs), counts=_parse_counts(logs), source=logs)
    if (output := item.get("output")) is not None:
        return OutputExpectation(
            stream=output["stream"],
            pattern=re.compile(output["pattern"]),
            exists=output.get("exists", True),
            source=output,
        )
    resource = item["resource"]
    return ResourceExpectation(
        attributes=_parse_attributes(resource), schema_url=_parse_value(resource, "schema_url"), source=resource
    )
