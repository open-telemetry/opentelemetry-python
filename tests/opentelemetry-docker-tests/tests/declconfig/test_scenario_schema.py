# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from unittest import TestCase

import jsonschema

from opentelemetry.proto.common.v1.common_pb2 import (
    AnyValue,
    ArrayValue,
    InstrumentationScope,
    KeyValue,
    KeyValueList,
)
from opentelemetry.proto.logs.v1.logs_pb2 import LogRecord, SeverityNumber
from opentelemetry.proto.metrics.v1.metrics_pb2 import (
    AggregationTemporality,
    Exemplar,
    Gauge,
    Histogram,
    HistogramDataPoint,
    Metric,
    NumberDataPoint,
    Sum,
)
from opentelemetry.proto.resource.v1.resource_pb2 import Resource
from opentelemetry.proto.trace.v1.trace_pb2 import Span, Status
from opentelemetry.test._otlp_test_server import (
    RecordedLogRecord,
    RecordedMetric,
    RecordedSpan,
)

from ._expect import (
    AttributesMatcher,
    Counts,
    DataPointMatcher,
    LinkMatcher,
    LiteralMatcher,
    LogMatcher,
    LogsExpectation,
    MetricExpectation,
    MetricMatcher,
    Mismatch,
    ResourceExpectation,
    ScopeMatcher,
    SpanMatcher,
    SpansExpectation,
    ValueMatcher,
    _describe_value,
    parse_value_matcher,
)
from ._scenario import (
    _SCHEMA_FILE,
    ExitedCondition,
    LogsCondition,
    MetricCondition,
    Received,
    SpansCondition,
    load_scenario,
    parse_scenario,
)

_SCENARIOS_DIR = Path(__file__).parent / "scenarios"
_TRACE_ID = b"\x0a" * 16
_OUTER_SPAN_ID = b"\x01" * 8
_INNER_SPAN_ID = b"\x02" * 8


def _build_attributes(**attributes: AnyValue) -> list[KeyValue]:
    return [KeyValue(key=key, value=value) for key, value in attributes.items()]


def _build_span(
    name: str,
    resource: Resource | None = None,
    scope: InstrumentationScope | None = None,
    **span_fields: Any,
) -> RecordedSpan:
    return RecordedSpan(
        span=Span(name=name, **span_fields),
        resource=resource or Resource(),
        scope=scope or InstrumentationScope(),
    )


def _build_metric(
    metric: Metric, resource: Resource | None = None, scope: InstrumentationScope | None = None
) -> RecordedMetric:
    return RecordedMetric(metric=metric, resource=resource or Resource(), scope=scope or InstrumentationScope())


def _build_log(
    body: str,
    resource: Resource | None = None,
    scope: InstrumentationScope | None = None,
    **log_fields: Any,
) -> RecordedLogRecord:
    return RecordedLogRecord(
        log_record=LogRecord(body=AnyValue(string_value=body), **log_fields),
        resource=resource or Resource(),
        scope=scope or InstrumentationScope(),
    )


def _build_scenario_doc(**overrides: Any) -> dict[str, Any]:
    return {"description": "test", "until": [{"spans": {}}], **overrides}


def _get_failures(expect: list[dict[str, Any]], received: Received) -> list[str]:
    failures = parse_scenario(_build_scenario_doc(expect=expect)).failed_expectations(received)
    return [str(failure) for failure in failures]


class TestScenarioSchema(TestCase):
    def test_bundled_scenarios_load(self):
        for path in sorted(_SCENARIOS_DIR.glob("*/scenario.yaml")):
            with self.subTest(scenario=path.parent.name):
                load_scenario(path)

    def test_defaults(self):
        scenario = parse_scenario(
            _build_scenario_doc(until=[{"spans": {}}, {"metric": {"name": "m", "min": 1}}, {"logs": {}}])
        )
        self.assertEqual(scenario.timeout, 30.0)
        self.assertEqual(scenario.env, {})
        self.assertEqual(
            scenario.until,
            [SpansCondition(), MetricCondition(name="m", min=1), LogsCondition()],
        )

    def test_parses_conditions(self):
        scenario = parse_scenario(
            _build_scenario_doc(
                timeout=5,
                env={"NAME": "value"},
                until=[
                    {"spans": {"min_count": 2, "name": "s"}},
                    {"metric": {"name": "m", "field": "count", "min": 3}},
                    {"logs": {"min_count": 4, "body_pattern": "a.*b"}},
                    {"exited": {}},
                ],
            )
        )
        self.assertEqual(scenario.timeout, 5.0)
        self.assertEqual(scenario.env, {"NAME": "value"})
        self.assertEqual(
            scenario.until,
            [
                SpansCondition(min_count=2, name="s"),
                MetricCondition(name="m", min=3, field="count"),
                LogsCondition(min_count=4, body_pattern=re.compile("a.*b")),
                ExitedCondition(),
            ],
        )

    def test_schema_is_valid(self):
        with open(_SCHEMA_FILE, encoding="utf-8") as schema_file:
            jsonschema.Draft202012Validator.check_schema(json.load(schema_file))

    def test_parses_expectations(self):
        scenario = parse_scenario(
            _build_scenario_doc(
                expect=[
                    {"resource": {"attributes": {"values": {"service.name": "svc"}, "strict": True}}},
                    {
                        "spans": {
                            "name": {"pattern": "^GET "},
                            "kind": "SERVER",
                            "status": {"code": "ERROR", "message": "boom"},
                            "parent": {"name": "outer", "root": True},
                            "links": [
                                {"trace_state": "k=v", "span": {"name": "producer"}, "attributes": {"values": {"n": 1}}}
                            ],
                            "scope": {"name": "lib", "version": {"exists": True}},
                            "count": 2,
                        }
                    },
                    {
                        "metric": {
                            "name": "requests",
                            "type": "sum",
                            "temporality": "CUMULATIVE",
                            "monotonic": True,
                            "data_point": {
                                "attributes": {"values": {"route": "/a"}},
                                "value": {"gte": 3, "lt": 10},
                                "explicit_bounds": [0, 5],
                            },
                            "max_count": 4,
                        }
                    },
                    {
                        "logs": {
                            "body": {"pattern": "user .* in"},
                            "severity_number": "WARN",
                            "event_name": "login",
                            "trace_context": True,
                            "span": {"name": "outer"},
                            "attributes": {"values": {"absent": {"exists": False}, "ratio": {"double": 1}}},
                            "count": 0,
                        }
                    },
                ]
            )
        )
        self.assertEqual(
            scenario.expect,
            [
                ResourceExpectation(
                    attributes=AttributesMatcher(matchers={"service.name": ValueMatcher(equals="svc")}, strict=True)
                ),
                SpansExpectation(
                    matcher=SpanMatcher(
                        name=ValueMatcher(pattern=re.compile("^GET ")),
                        kind=LiteralMatcher("SERVER"),
                        status_code=LiteralMatcher("ERROR"),
                        status_message=ValueMatcher(equals="boom"),
                        parent=SpanMatcher(name=ValueMatcher(equals="outer"), root=LiteralMatcher(True)),
                        links=(
                            LinkMatcher(
                                trace_state=ValueMatcher(equals="k=v"),
                                span=SpanMatcher(name=ValueMatcher(equals="producer")),
                                attributes=AttributesMatcher(matchers={"n": ValueMatcher(equals=1)}),
                            ),
                        ),
                        scope=ScopeMatcher(name=ValueMatcher(equals="lib"), version=ValueMatcher(exists=True)),
                    ),
                    counts=Counts(count=2),
                ),
                MetricExpectation(
                    matcher=MetricMatcher(
                        name=ValueMatcher(equals="requests"),
                        type=LiteralMatcher("sum"),
                        temporality=LiteralMatcher("CUMULATIVE"),
                        monotonic=LiteralMatcher(True),
                        data_point=DataPointMatcher(
                            value=ValueMatcher(bounds=(("gte", 3), ("lt", 10))),
                            explicit_bounds=LiteralMatcher([0, 5]),
                            attributes=AttributesMatcher(matchers={"route": ValueMatcher(equals="/a")}),
                        ),
                    ),
                    counts=Counts(max_count=4),
                ),
                LogsExpectation(
                    matcher=LogMatcher(
                        body=ValueMatcher(pattern=re.compile("user .* in")),
                        severity_number=LiteralMatcher("WARN"),
                        event_name=ValueMatcher(equals="login"),
                        trace_context=LiteralMatcher(True),
                        span=SpanMatcher(name=ValueMatcher(equals="outer")),
                        attributes=AttributesMatcher(
                            matchers={
                                "absent": ValueMatcher(exists=False),
                                "ratio": ValueMatcher(equals=1.0),
                            }
                        ),
                    ),
                    counts=Counts(count=0),
                ),
            ],
        )

    def test_invalid_documents(self):
        cases = {
            "missing description": {"until": [{"spans": {}}]},
            "missing until": {"description": "test"},
            "empty until": _build_scenario_doc(until=[]),
            "unknown top-level key": _build_scenario_doc(extra=1),
            "non-positive timeout": _build_scenario_doc(timeout=0),
            "unknown signal": _build_scenario_doc(until=[{"traces": {}}]),
            "two signals in one item": _build_scenario_doc(until=[{"spans": {}, "logs": {}}]),
            "unknown condition key": _build_scenario_doc(until=[{"spans": {"count": 1}}]),
            "zero min_count": _build_scenario_doc(until=[{"spans": {"min_count": 0}}]),
            "metric missing min": _build_scenario_doc(until=[{"metric": {"name": "m"}}]),
            "bad metric field": _build_scenario_doc(until=[{"metric": {"name": "m", "field": "max", "min": 1}}]),
            "unknown expect signal": _build_scenario_doc(expect=[{"traces": {}}]),
            "two signals in one expect item": _build_scenario_doc(expect=[{"spans": {}, "logs": {}}]),
            "unknown span field": _build_scenario_doc(expect=[{"spans": {"events": []}}]),
            "count with min_count": _build_scenario_doc(expect=[{"spans": {"count": 1, "min_count": 1}}]),
            "count with max_count": _build_scenario_doc(expect=[{"logs": {"count": 1, "max_count": 1}}]),
            "zero max_count": _build_scenario_doc(expect=[{"logs": {"max_count": 0}}]),
            "count on nested span matcher": _build_scenario_doc(expect=[{"spans": {"parent": {"count": 1}}}]),
            "root with parent": _build_scenario_doc(expect=[{"spans": {"root": True, "parent": {}}}]),
            "bad span kind": _build_scenario_doc(expect=[{"spans": {"kind": "server"}}]),
            "bad status code": _build_scenario_doc(expect=[{"spans": {"status": {"code": "FAILED"}}}]),
            "bad severity": _build_scenario_doc(expect=[{"logs": {"severity_number": "WARNING"}}]),
            "bad temporality": _build_scenario_doc(expect=[{"metric": {"temporality": "cumulative"}}]),
            "bad metric type": _build_scenario_doc(expect=[{"metric": {"type": "counter"}}]),
            "unknown data point field": _build_scenario_doc(expect=[{"metric": {"data_point": {"buckets": []}}}]),
            "string data point value": _build_scenario_doc(expect=[{"metric": {"data_point": {"value": "3"}}}]),
            "pattern on data point value": _build_scenario_doc(
                expect=[{"metric": {"data_point": {"value": {"pattern": "3"}}}}]
            ),
            "exists false with other operators": _build_scenario_doc(
                expect=[{"spans": {"attributes": {"values": {"a": {"exists": False, "pattern": "x"}}}}}]
            ),
            "typed literal with two types": _build_scenario_doc(
                expect=[{"spans": {"attributes": {"values": {"a": {"int": 1, "double": 1.0}}}}}]
            ),
            "typed literal with operator": _build_scenario_doc(
                expect=[{"spans": {"attributes": {"values": {"a": {"int": 1, "gt": 0}}}}}]
            ),
            "wrongly typed literal": _build_scenario_doc(
                expect=[{"spans": {"attributes": {"values": {"a": {"int": "1"}}}}}]
            ),
            "empty operators": _build_scenario_doc(expect=[{"spans": {"attributes": {"values": {"a": {}}}}}]),
            "empty resource": _build_scenario_doc(expect=[{"resource": {}}]),
            "resource with count": _build_scenario_doc(
                expect=[{"resource": {"attributes": {"values": {}}, "count": 1}}]
            ),
            "empty attributes": _build_scenario_doc(expect=[{"spans": {"attributes": {}}}]),
            "unwrapped attributes": _build_scenario_doc(expect=[{"spans": {"attributes": {"a": 1}}}]),
            "unknown scope field": _build_scenario_doc(expect=[{"spans": {"scope": {"schema_url": "x"}}}]),
            "non-string env value": _build_scenario_doc(env={"N": 1}),
            "exited with fields": _build_scenario_doc(until=[{"exited": {"code": 0}}]),
            "output without pattern": _build_scenario_doc(expect=[{"output": {"stream": "stdout"}}]),
            "bad output stream": _build_scenario_doc(expect=[{"output": {"stream": "stdin", "pattern": "x"}}]),
            "string link_count": _build_scenario_doc(expect=[{"spans": {"link_count": "1"}}]),
            "pattern on exemplar_count": _build_scenario_doc(
                expect=[{"metric": {"data_point": {"exemplar_count": {"pattern": "1"}}}}]
            ),
        }
        for case, document in cases.items():
            with self.subTest(case=case), self.assertRaises(jsonschema.ValidationError):
                parse_scenario(document)

    def test_invalid_body_pattern(self):
        with self.assertRaises(re.error):
            parse_scenario(_build_scenario_doc(until=[{"logs": {"body_pattern": "("}}]))

    def test_invalid_expect_pattern(self):
        with self.assertRaises(re.error):
            parse_scenario(_build_scenario_doc(expect=[{"spans": {"name": {"pattern": "("}}}]))


class TestConditions(TestCase):
    def test_spans(self):
        received = Received(spans=[_build_span("a"), _build_span("b"), _build_span("a")])
        cases = [
            (SpansCondition(min_count=3), True, "spans(name=None): 3/3"),
            (SpansCondition(min_count=4), False, "spans(name=None): 3/4"),
            (SpansCondition(min_count=2, name="a"), True, "spans(name='a'): 2/2"),
            (SpansCondition(name="c"), False, "spans(name='c'): 0/1"),
        ]
        for condition, met, progress in cases:
            with self.subTest(condition=condition):
                self.assertEqual(condition.satisfied(received), met)
                self.assertEqual(condition.progress(received), progress)

    def test_metrics(self):
        counter = Metric(
            name="counter",
            sum=Sum(data_points=[NumberDataPoint(as_int=2), NumberDataPoint(as_int=5)]),
        )
        gauge = Metric(name="gauge", gauge=Gauge(data_points=[NumberDataPoint(as_double=1.5)]))
        histogram = Metric(
            name="histogram",
            histogram=Histogram(data_points=[HistogramDataPoint(count=4, sum=10.0)]),
        )
        received = Received(metrics=[_build_metric(counter), _build_metric(gauge), _build_metric(histogram)])
        cases = [
            (MetricCondition(name="counter", min=5), True),
            (MetricCondition(name="counter", min=6), False),
            (MetricCondition(name="gauge", min=1.5), True),
            (MetricCondition(name="histogram", field="count", min=4), True),
            (MetricCondition(name="histogram", field="sum", min=10.5), False),
            (MetricCondition(name="missing", min=0), False),
        ]
        for condition, met in cases:
            with self.subTest(condition=condition):
                self.assertEqual(condition.satisfied(received), met)

        self.assertEqual(
            MetricCondition(name="missing", min=0).progress(received),
            "metric(name='missing', field='value'): max None (need >= 0)",
        )

    def test_metric_field_mismatch(self):
        received = Received(
            metrics=[_build_metric(Metric(name="gauge", gauge=Gauge(data_points=[NumberDataPoint(as_int=1)])))]
        )
        cases = [
            MetricCondition(name="gauge", field="count", min=1),
            MetricCondition(name="gauge", field="sum", min=1),
        ]
        for condition in cases:
            with self.subTest(condition=condition), self.assertRaises(ValueError):
                condition.satisfied(received)

    def test_logs(self):
        received = Received(
            logs=[_build_log("user alice logged in"), _build_log("startup"), _build_log("user bob logged in")]
        )
        cases = [
            (LogsCondition(min_count=3), True, "logs(body_pattern=None): 3/3"),
            (
                LogsCondition(min_count=2, body_pattern=re.compile(r"user .* in")),
                True,
                "logs(body_pattern='user .* in'): 2/2",
            ),
            (LogsCondition(body_pattern=re.compile("shutdown")), False, "logs(body_pattern='shutdown'): 0/1"),
        ]
        for condition, met, progress in cases:
            with self.subTest(condition=condition):
                self.assertEqual(condition.satisfied(received), met)
                self.assertEqual(condition.progress(received), progress)

    def test_exited(self):
        cases = [(Received(), False, "exited: False"), (Received(exited=True), True, "exited: True")]
        for received, met, progress in cases:
            with self.subTest(exited=received.exited):
                self.assertEqual(ExitedCondition().satisfied(received), met)
                self.assertEqual(ExitedCondition().progress(received), progress)


class TestExpectations(TestCase):
    def test_mismatch_str(self):
        cases = [
            (Mismatch(("name",), "a", "b"), "name: expected a, got b"),
            (Mismatch(("attributes", "['k']"), "1", "<absent>"), "attributes['k']: expected 1, got <absent>"),
            (Mismatch(("value",), "3", "4").nested("data_point"), "data_point.value: expected 3, got 4"),
            (
                Mismatch(("name",), "a span", "<absent>").nested("span").nested("links[0]"),
                "links[0].span.name: expected a span, got <absent>",
            ),
        ]
        for mismatch, text in cases:
            with self.subTest(mismatch=mismatch):
                self.assertEqual(str(mismatch), text)

    def test_value_matchers(self):
        int_value = AnyValue(int_value=5)
        double_value = AnyValue(double_value=5.0)
        string_value = AnyValue(string_value="abc")
        array_value = AnyValue(array_value=ArrayValue(values=[AnyValue(int_value=1), AnyValue(string_value="a")]))
        kvlist_value = AnyValue(
            kvlist_value=KeyValueList(values=_build_attributes(b=AnyValue(bool_value=True), a=AnyValue(int_value=1)))
        )
        cases = [
            (5, int_value, True),
            (5, double_value, False),
            (5.0, double_value, True),
            (5.0, int_value, False),
            ("5", int_value, False),
            ({"double": 5}, double_value, True),
            ({"int": 5}, double_value, False),
            ({"string": "abc"}, string_value, True),
            (True, AnyValue(bool_value=True), True),
            (True, AnyValue(int_value=1), False),
            (1, AnyValue(bool_value=True), False),
            ([1, "a"], array_value, True),
            ([1.0, "a"], array_value, False),
            (["a", 1], array_value, False),
            ({"kvlist": {"a": 1, "b": True}}, kvlist_value, True),
            ({"kvlist": {"a": 1}}, kvlist_value, False),
            ({"kvlist": {"a": True, "b": True}}, kvlist_value, False),
            (
                [1, "a"],
                AnyValue(array_value=ArrayValue(values=[AnyValue(bool_value=True), AnyValue(string_value="a")])),
                False,
            ),
            ({"pattern": "^ab"}, string_value, True),
            ({"pattern": "^b"}, string_value, False),
            ({"pattern": "5"}, int_value, False),
            ({"gte": 5, "lt": 6}, int_value, True),
            ({"gte": 5, "lt": 6}, double_value, True),
            ({"gt": 5}, int_value, False),
            ({"gt": 0}, string_value, False),
            ({"exists": True, "pattern": "c$"}, string_value, True),
            ({"exists": True}, None, False),
            ({"exists": False}, None, True),
            ({"exists": False}, int_value, False),
            (5, None, False),
        ]
        for spec, value, matches in cases:
            with self.subTest(spec=spec, value=value):
                attributes = _build_attributes(key=value) if value is not None else []
                matcher = AttributesMatcher(matchers={"key": parse_value_matcher(spec)})
                self.assertEqual(not list(matcher.check("attributes", attributes)), matches)

    def test_describe_value(self):
        cases = [
            (5, "5"),
            (5.0, "5.0"),
            ("5", "'5'"),
            ("true", "'true'"),
            ("", "''"),
            ("abc", "abc"),
            (True, "true"),
            ([1, "a"], "[1, a]"),
            ({"a": 1, "b": [2.5]}, "{a: 1, b: [2.5]}"),
            (None, "<absent>"),
        ]
        for value, text in cases:
            with self.subTest(value=value):
                self.assertEqual(_describe_value(value), text)

    def test_attributes_strict(self):
        attributes = _build_attributes(a=AnyValue(int_value=1), b=AnyValue(int_value=2))
        cases = [
            ({"attributes": {"values": {"a": 1}}}, []),
            ({"attributes": {"values": {"a": 1}, "strict": True}}, ["attributes: expected no unlisted keys, got b"]),
            ({"attributes": {"values": {"a": 1, "b": 2, "c": {"exists": False}}, "strict": True}}, []),
            ({"attributes": {"strict": True}}, ["attributes: expected no unlisted keys, got a, b"]),
        ]
        received = Received(spans=[_build_span("s", attributes=attributes)])
        for spec, problems in cases:
            with self.subTest(spec=spec):
                failures = _get_failures([{"spans": spec}], received)
                self.assertEqual(failures != [], bool(problems))
                for problem in problems:
                    self.assertIn(problem, failures[0])

    def test_resource(self):
        service = Resource(attributes=_build_attributes(**{"service.name": AnyValue(string_value="svc")}))
        other = Resource(attributes=_build_attributes(**{"service.name": AnyValue(string_value="other")}))
        expect = [{"resource": {"attributes": {"values": {"service.name": "svc"}}}}]
        cases = [
            ("all match", Received(spans=[_build_span("s", service)], logs=[_build_log("b", service)]), None),
            (
                "one mismatch",
                Received(spans=[_build_span("s", service)], logs=[_build_log("b", other), _build_log("c", other)]),
                "2 of 3 items have a non-matching resource\n  log: attributes['service.name']: expected svc, got other",
            ),
            ("nothing received", Received(), "nothing received"),
        ]
        for case, received, problem in cases:
            with self.subTest(case=case):
                failures = _get_failures(expect, received)
                if problem is None:
                    self.assertEqual(failures, [])
                else:
                    self.assertEqual(len(failures), 1)
                    self.assertIn(problem, failures[0])

    def test_resource_schema_url(self):
        resource = Resource(attributes=_build_attributes(**{"service.name": AnyValue(string_value="svc")}))
        span = _build_span("s", resource)
        cases = [
            ({"pattern": "1\\.26"}, "https://opentelemetry.io/schemas/1.26.0", None),
            ("https://opentelemetry.io/schemas/1.26.0", "https://opentelemetry.io/schemas/1.27.0", "schema_url"),
            ({"exists": False}, "", None),
            ({"exists": True}, "", "schema_url: expected present, got <absent>"),
        ]
        for spec, schema_url, problem in cases:
            with self.subTest(spec=spec, schema_url=schema_url):
                span.resource_schema_url = schema_url
                failures = _get_failures([{"resource": {"schema_url": spec}}], Received(spans=[span]))
                if problem is None:
                    self.assertEqual(failures, [])
                else:
                    self.assertEqual(len(failures), 1)
                    self.assertIn(problem, failures[0])

    def test_output(self):
        received = Received(stdout='{"name": "console-span"}', stderr="Failed to auto initialize OpenTelemetry")
        cases = [
            ({"stream": "stdout", "pattern": '"name": "console-span"'}, None),
            ({"stream": "stderr", "pattern": "console-span"}, "stderr has no match for 'console-span'"),
            (
                {"stream": "stderr", "pattern": "Failed to auto", "exists": False},
                "stderr has a match for 'Failed to auto'",
            ),
            ({"stream": "stdout", "pattern": "Traceback", "exists": False}, None),
        ]
        for spec, problem in cases:
            with self.subTest(spec=spec):
                failures = _get_failures([{"output": spec}], received)
                if problem is None:
                    self.assertEqual(failures, [])
                else:
                    self.assertEqual(len(failures), 1)
                    self.assertIn(problem, failures[0])

    def test_link_count(self):
        target = _build_span("target", trace_id=_TRACE_ID, span_id=_OUTER_SPAN_ID)
        link = Span.Link(trace_id=_TRACE_ID, span_id=_OUTER_SPAN_ID)
        received = Received(spans=[target, _build_span("linked", links=[link, link])])
        cases = [
            ({"link_count": 2}, True),
            ({"link_count": 1}, False),
            ({"link_count": {"gte": 1, "lt": 3}}, True),
            ({"name": "target", "link_count": 0}, True),
        ]
        for spec, met in cases:
            with self.subTest(spec=spec):
                spec = {"name": "linked", **spec}
                self.assertEqual(_get_failures([{"spans": spec}], received) == [], met)

    def test_exemplar_count(self):
        sum_metric = Metric(
            name="requests",
            sum=Sum(data_points=[NumberDataPoint(as_int=1, exemplars=[Exemplar(as_int=1), Exemplar(as_int=1)])]),
        )
        received = Received(metrics=[_build_metric(sum_metric)])
        cases = [
            ({"exemplar_count": 2}, True),
            ({"exemplar_count": {"gte": 1}}, True),
            ({"exemplar_count": 0}, False),
        ]
        for data_point, met in cases:
            with self.subTest(data_point=data_point):
                expect = [{"metric": {"name": "requests", "data_point": data_point}}]
                self.assertEqual(_get_failures(expect, received) == [], met)

    def test_spans(self):
        outer = _build_span(
            "outer",
            scope=InstrumentationScope(name="lib", version="1.0"),
            trace_id=_TRACE_ID,
            span_id=_OUTER_SPAN_ID,
        )
        inner = _build_span(
            "GET /a",
            trace_id=_TRACE_ID,
            span_id=_INNER_SPAN_ID,
            parent_span_id=_OUTER_SPAN_ID,
            kind=Span.SPAN_KIND_SERVER,
            status=Status(code=Status.STATUS_CODE_ERROR, message="boom"),
            trace_state="k=v",
            links=[
                Span.Link(
                    trace_id=_TRACE_ID,
                    span_id=_OUTER_SPAN_ID,
                    attributes=_build_attributes(n=AnyValue(int_value=1)),
                )
            ],
            attributes=_build_attributes(**{"http.method": AnyValue(string_value="GET")}),
        )
        orphan = _build_span("orphan", trace_id=_TRACE_ID, span_id=b"\x03" * 8, parent_span_id=b"\x09" * 8)
        received = Received(spans=[outer, inner, orphan])
        cases = [
            ({}, True),
            ({"count": 3}, True),
            ({"max_count": 2}, False),
            ({"name": {"pattern": "^GET "}, "kind": "SERVER"}, True),
            ({"name": "GET /a", "kind": "INTERNAL"}, False),
            ({"status": {"code": "ERROR", "message": {"pattern": "boo"}}}, True),
            ({"status": {"code": "OK"}}, False),
            ({"trace_state": "k=v"}, True),
            ({"root": True, "count": 1}, True),
            ({"root": False, "count": 2}, True),
            ({"name": "GET /a", "parent": {"name": "outer", "root": True}}, True),
            ({"name": "GET /a", "parent": {"name": "other"}}, False),
            ({"name": "orphan", "parent": {}}, False),
            ({"links": [{"attributes": {"values": {"n": 1}}, "span": {"name": "outer"}}]}, True),
            ({"links": [{"attributes": {"values": {"n": 2}}}]}, False),
            ({"links": [{"trace_state": {"exists": True}}]}, False),
            ({"name": "outer", "scope": {"name": "lib", "version": "1.0"}}, True),
            ({"name": "outer", "scope": {"version": {"exists": False}}}, False),
            ({"attributes": {"values": {"http.method": "GET"}}, "count": 1}, True),
            ({"name": "missing", "count": 0}, True),
            ({"name": "outer", "count": 0}, False),
        ]
        for spec, met in cases:
            with self.subTest(spec=spec):
                self.assertEqual(_get_failures([{"spans": spec}], received) == [], met)

    def test_metrics(self):
        def build_sum(value: int, route: str) -> Metric:
            return Metric(
                name="requests",
                unit="1",
                sum=Sum(
                    aggregation_temporality=AggregationTemporality.AGGREGATION_TEMPORALITY_CUMULATIVE,
                    is_monotonic=True,
                    data_points=[
                        NumberDataPoint(as_int=value, attributes=_build_attributes(route=AnyValue(string_value=route)))
                    ],
                ),
            )

        histogram = Metric(
            name="duration",
            histogram=Histogram(
                aggregation_temporality=AggregationTemporality.AGGREGATION_TEMPORALITY_DELTA,
                data_points=[
                    HistogramDataPoint(count=4, sum=10.0, min=1.0, explicit_bounds=[0, 5], bucket_counts=[0, 3, 1])
                ],
            ),
        )
        gauge = Metric(name="temperature", gauge=Gauge(data_points=[NumberDataPoint(as_double=21.5)]))
        received = Received(
            metrics=[
                _build_metric(build_sum(1, "/a"), scope=InstrumentationScope(name="app")),
                _build_metric(build_sum(3, "/a")),
                _build_metric(histogram),
                _build_metric(gauge),
            ]
        )
        cases = [
            ({"name": "requests", "count": 2}, True),
            ({"name": "requests", "data_point": {"value": {"gte": 3}}, "count": 1}, True),
            ({"name": "requests", "data_point": {"value": 3}}, True),
            ({"name": "requests", "data_point": {"value": 3.0}}, False),
            ({"name": "requests", "data_point": {"attributes": {"values": {"route": "/b"}}}, "count": 0}, True),
            ({"name": "requests", "type": "sum", "unit": "1", "temporality": "CUMULATIVE", "monotonic": True}, True),
            ({"name": "requests", "temporality": "DELTA"}, False),
            ({"name": "requests", "scope": {"name": "app"}, "count": 1}, True),
            ({"name": "requests", "type": "gauge"}, False),
            ({"name": "requests", "description": {"exists": False}}, True),
            ({"name": "duration", "temporality": "DELTA", "data_point": {"count": 4, "sum": {"gt": 9}}}, True),
            ({"name": "duration", "data_point": {"sum": 10, "min": 1, "max": {"exists": False}}}, True),
            ({"name": "duration", "data_point": {"max": {"exists": True}}}, False),
            ({"name": "duration", "data_point": {"explicit_bounds": [0, 5], "bucket_counts": [0, 3, 1]}}, True),
            ({"name": "duration", "data_point": {"explicit_bounds": [0, 10]}}, False),
            ({"name": "temperature", "data_point": {"value": 21.5}}, True),
            ({"type": "gauge", "data_point": {"value": {"lt": 20}}}, False),
        ]
        for spec, met in cases:
            with self.subTest(spec=spec):
                self.assertEqual(_get_failures([{"metric": spec}], received) == [], met)

    def test_metric_field_mismatch(self):
        gauge = Metric(name="gauge", gauge=Gauge(data_points=[NumberDataPoint(as_int=1)]))
        histogram = Metric(name="histogram", histogram=Histogram(data_points=[HistogramDataPoint(count=1)]))
        received = Received(metrics=[_build_metric(gauge), _build_metric(histogram)])
        cases = [
            {"name": "gauge", "temporality": "CUMULATIVE"},
            {"name": "gauge", "monotonic": True},
            {"name": "gauge", "data_point": {"count": 1}},
            {"name": "histogram", "data_point": {"value": 1}},
            {"data_point": {"explicit_bounds": []}},
        ]
        for spec in cases:
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                _get_failures([{"metric": spec}], received)

    def test_logs(self):
        span = _build_span("handler", trace_id=_TRACE_ID, span_id=_OUTER_SPAN_ID)
        in_span = _build_log(
            "user alice logged in",
            scope=InstrumentationScope(name="auth"),
            trace_id=_TRACE_ID,
            span_id=_OUTER_SPAN_ID,
            severity_number=SeverityNumber.SEVERITY_NUMBER_WARN,
            severity_text="WARN",
            event_name="login",
            attributes=_build_attributes(user=AnyValue(string_value="alice")),
        )
        orphan = _build_log("lost", trace_id=_TRACE_ID, span_id=_INNER_SPAN_ID)
        plain = _build_log("startup")
        received = Received(spans=[span], logs=[in_span, orphan, plain])
        cases = [
            ({"body": {"pattern": "user .* in"}, "count": 1}, True),
            ({"body": "startup"}, True),
            ({"body": {"string": "start"}}, False),
            ({"severity_number": "WARN", "severity_text": "WARN", "event_name": "login"}, True),
            ({"severity_number": "WARN2"}, False),
            ({"trace_context": True, "count": 2}, True),
            ({"trace_context": False, "count": 1}, True),
            ({"span": {"name": "handler"}, "count": 1}, True),
            ({"body": "lost", "span": {}}, False),
            ({"scope": {"name": "auth"}, "attributes": {"values": {"user": "alice"}}}, True),
            ({"event_name": {"exists": True}, "count": 1}, True),
            ({"severity_number": "ERROR", "count": 0}, True),
        ]
        for spec, met in cases:
            with self.subTest(spec=spec):
                self.assertEqual(_get_failures([{"logs": spec}], received) == [], met)

    def test_failure_messages(self):
        received = Received(spans=[_build_span("basic-span"), _build_span("other"), _build_span("other")])
        cases = [
            (
                {"name": "basic-span", "kind": "SERVER"},
                "spans: {name: basic-span, kind: SERVER}\n"
                "  matched 0, expected >= 1\n"
                "  closest 'basic-span': kind: expected SERVER, got UNSPECIFIED\n"
                "  closest 'other': name: expected basic-span, got other; "
                "kind: expected SERVER, got UNSPECIFIED",
            ),
            (
                {"name": "other", "count": 0},
                "spans: {name: other, count: 0}\n  matched 2, expected == 0\n  matched 'other'\n  matched 'other'",
            ),
            (
                {"kind": "SERVER", "min_count": 2, "max_count": 3},
                "spans: {kind: SERVER, min_count: 2, max_count: 3}\n"
                "  matched 0, expected >= 2 and <= 3\n"
                "  closest 'basic-span': kind: expected SERVER, got UNSPECIFIED\n"
                "  closest 'other': kind: expected SERVER, got UNSPECIFIED",
            ),
        ]
        for spec, message in cases:
            with self.subTest(spec=spec):
                self.assertEqual(_get_failures([{"spans": spec}], received), [message])
        self.assertEqual(
            _get_failures([{"logs": {}}], received),
            ["logs: {}\n  matched 0, expected >= 1\n  no logs received"],
        )
