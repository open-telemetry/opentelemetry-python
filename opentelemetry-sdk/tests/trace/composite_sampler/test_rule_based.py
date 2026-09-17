# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace._sampling_experimental import (
    composable_always_off,
    composable_always_on,
    composable_rule_based,
    composite_sampler,
)
from opentelemetry.sdk.trace._sampling_experimental._composable import (
    SamplingIntent,
)
from opentelemetry.sdk.trace._sampling_experimental._rule_based import (
    AllPredicate,
    AlwaysMatchPredicate,
    AttributePatternsPredicate,
    AttributePredicate,
    AttributeValuesPredicate,
    ParentPredicate,
    SpanKindPredicate,
    SpanTypePredicate,
    call_predicate,
)
from opentelemetry.sdk.trace.id_generator import RandomIdGenerator
from opentelemetry.sdk.trace.sampling import Decision
from opentelemetry.trace import (
    NonRecordingSpan,
    SpanContext,
    SpanKind,
    TraceFlags,
    set_span_in_context,
)

TRACE_ID = int("00112233445566778800000000000000", 16)
SPAN_ID = int("0123456789abcdef", 16)


class NameIsFooPredicate:
    def __call__(
        self,
        parent_ctx,
        name,
        span_kind,
        attributes,
        links,
        trace_state,
    ):
        return name == "foo"

    def __str__(self):
        return "NameIsFooPredicate"


def _predicate_result(
    predicate,
    *,
    parent_ctx=None,
    span_kind=None,
    attributes=None,
    span_type=None,
    instrumentation_scope=None,
    resource=None,
):
    return call_predicate(
        predicate,
        parent_ctx,
        "span",
        span_kind,
        attributes,
        None,
        None,
        span_type=span_type,
        instrumentation_scope=instrumentation_scope,
        resource=resource,
    )


def _parent_context(is_remote: bool):
    return set_span_in_context(
        NonRecordingSpan(
            SpanContext(
                TRACE_ID,
                SPAN_ID,
                is_remote=is_remote,
                trace_flags=TraceFlags.get_default(),
            )
        )
    )


def test_description_with_no_rules():
    assert composable_rule_based(rules=[]).get_description() == "ComposableRuleBased{[]}"


def test_always_match_predicate():
    assert _predicate_result(AlwaysMatchPredicate()) is True
    assert str(AlwaysMatchPredicate()) == "AlwaysMatch"


def test_all_predicate_matches_when_all_predicates_match():
    predicate = AllPredicate(
        [
            AttributeValuesPredicate("http.route", ["/users"]),
            SpanKindPredicate([SpanKind.SERVER]),
        ]
    )

    assert (
        _predicate_result(
            predicate,
            span_kind=SpanKind.SERVER,
            attributes={"http.route": "/users"},
        )
        is True
    )


def test_all_predicate_does_not_match_when_any_predicate_does_not_match():
    predicate = AllPredicate(
        [
            AttributeValuesPredicate("http.route", ["/users"]),
            SpanKindPredicate([SpanKind.SERVER]),
        ]
    )

    assert (
        _predicate_result(
            predicate,
            span_kind=SpanKind.CLIENT,
            attributes={"http.route": "/users"},
        )
        is False
    )


def test_attribute_values_predicate_no_attributes():
    assert _predicate_result(AttributeValuesPredicate("http.route", ["/users"])) is False


def test_attribute_values_predicate_stringifies_values():
    assert (
        _predicate_result(
            AttributeValuesPredicate("http.response.status_code", ["404"]),
            attributes={"http.response.status_code": 404},
        )
        is True
    )


def test_attribute_values_predicate_matches_array_item():
    assert (
        _predicate_result(
            AttributeValuesPredicate("http.request.method", ["POST"]),
            attributes={"http.request.method": ("GET", "POST")},
        )
        is True
    )


def test_attribute_values_predicate_no_match():
    assert (
        _predicate_result(
            AttributeValuesPredicate("http.route", ["/users"]),
            attributes={"http.route": "/health"},
        )
        is False
    )


def test_attribute_patterns_predicate_includes_all_by_default():
    assert (
        _predicate_result(
            AttributePatternsPredicate("http.route"),
            attributes={"http.route": "/users"},
        )
        is True
    )


def test_attribute_patterns_predicate_include_exclude_precedence():
    predicate = AttributePatternsPredicate(
        "http.route",
        included=["/api/*"],
        excluded=["/api/private/*"],
    )

    assert _predicate_result(predicate, attributes={"http.route": "/api/users"}) is True
    assert _predicate_result(predicate, attributes={"http.route": "/api/private/user"}) is False


def test_attribute_patterns_predicate_is_case_sensitive():
    assert (
        _predicate_result(
            AttributePatternsPredicate("http.route", included=["/api/*"]),
            attributes={"http.route": "/API/users"},
        )
        is False
    )


def test_attribute_patterns_predicate_matches_array_item():
    assert (
        _predicate_result(
            AttributePatternsPredicate("http.request.method", ["POST"]),
            attributes={"http.request.method": ("GET", "POST")},
        )
        is True
    )


def test_span_kind_predicate():
    predicate = SpanKindPredicate([SpanKind.SERVER])

    assert _predicate_result(predicate, span_kind=SpanKind.SERVER) is True
    assert _predicate_result(predicate, span_kind=SpanKind.CLIENT) is False
    assert _predicate_result(predicate) is False


def test_parent_predicate_matches_no_parent():
    assert _predicate_result(ParentPredicate(["none"])) is True
    assert _predicate_result(ParentPredicate(["local"])) is False


def test_parent_predicate_matches_local_parent():
    local_parent_ctx = _parent_context(is_remote=False)

    assert _predicate_result(ParentPredicate(["local"]), parent_ctx=local_parent_ctx) is True
    assert _predicate_result(ParentPredicate(["remote"]), parent_ctx=local_parent_ctx) is False


def test_parent_predicate_matches_remote_parent():
    remote_parent_ctx = _parent_context(is_remote=True)

    assert _predicate_result(ParentPredicate(["remote"]), parent_ctx=remote_parent_ctx) is True
    assert _predicate_result(ParentPredicate(["local"]), parent_ctx=remote_parent_ctx) is False


def test_description_with_rules():
    rules = [
        (AttributeValuesPredicate("foo", ["bar"]), composable_always_on()),
        (NameIsFooPredicate(), composable_always_off()),
    ]
    assert (
        composable_rule_based(rules=rules).get_description()
        == "ComposableRuleBased{[(foo in [bar]:ComposableAlwaysOn),(NameIsFooPredicate:ComposableAlwaysOff)]}"
    )


def test_sampling_intent_match():
    rules = [
        (NameIsFooPredicate(), composable_always_on()),
    ]
    assert composable_rule_based(rules=rules).sampling_intent(None, "foo", None, {}, None, None).threshold == 0


def test_sampling_intent_no_match():
    rules = [
        (NameIsFooPredicate(), composable_always_on()),
    ]
    assert composable_rule_based(rules=rules).sampling_intent(None, "test", None, {}, None, None).threshold == -1


def test_should_sample_match():
    rules = [
        (NameIsFooPredicate(), composable_always_on()),
    ]
    sampler = composite_sampler(composable_rule_based(rules=rules))

    res = sampler.should_sample(
        None,
        RandomIdGenerator().generate_trace_id(),
        "foo",
        None,
        None,
        None,
        None,
    )

    assert res.decision == Decision.RECORD_AND_SAMPLE
    assert res.trace_state is not None
    assert res.trace_state.get("ot", "") == "th:0"


def test_should_sample_match_multiple_rules():
    rules = [
        (AttributeValuesPredicate("foo", ["bar"]), composable_always_off()),
        (NameIsFooPredicate(), composable_always_on()),
    ]
    sampler = composite_sampler(composable_rule_based(rules=rules))

    res = sampler.should_sample(
        None,
        RandomIdGenerator().generate_trace_id(),
        "foo",
        None,
        None,
        None,
        None,
    )

    assert res.decision == Decision.RECORD_AND_SAMPLE
    assert res.trace_state is not None
    assert res.trace_state.get("ot", "") == "th:0"


def test_should_sample_no_match():
    rules = [
        (NameIsFooPredicate(), composable_always_on()),
    ]
    sampler = composite_sampler(composable_rule_based(rules=rules))

    res = sampler.should_sample(
        None,
        RandomIdGenerator().generate_trace_id(),
        "test",
        None,
        None,
        None,
        None,
    )

    assert res.decision == Decision.DROP
    assert res.trace_state is None


def test_attribute_predicate_no_attributes():
    rules = [
        (AttributePredicate("foo", "bar"), composable_always_on()),
    ]
    assert composable_rule_based(rules=rules).sampling_intent(None, "span", None, None, None, None).threshold == -1


def test_attribute_predicate_no_match():
    rules = [
        (AttributePredicate("foo", "bar"), composable_always_on()),
    ]
    assert (
        composable_rule_based(rules=rules).sampling_intent(None, "span", None, {"foo": "foo"}, None, None).threshold
        == -1
    )


def test_attribute_predicate_match():
    rules = [
        (AttributePredicate("foo", "bar"), composable_always_on()),
    ]
    assert (
        composable_rule_based(rules=rules).sampling_intent(None, "span", None, {"foo": "bar"}, None, None).threshold
        == 0
    )


def test_span_type_predicate():
    predicate = SpanTypePredicate(["http.server.request", "db.client.call"])

    assert _predicate_result(predicate, span_type="http.server.request") is True
    assert _predicate_result(predicate, span_type="db.client.call") is True
    assert _predicate_result(predicate, span_type="messaging.producer.send") is False
    assert _predicate_result(predicate) is False
    assert str(predicate) == "span_type in [db.client.call,http.server.request]"


def test_span_type_predicate_is_anded_with_other_conditions():
    predicate = AllPredicate(
        [
            SpanTypePredicate(["http.server.request"]),
            SpanKindPredicate([SpanKind.SERVER]),
        ]
    )

    assert _predicate_result(predicate, span_kind=SpanKind.SERVER, span_type="http.server.request") is True
    assert _predicate_result(predicate, span_kind=SpanKind.CLIENT, span_type="http.server.request") is False


def test_rule_based_samples_on_span_type():
    sampler = composite_sampler(
        composable_rule_based(
            [
                (SpanTypePredicate(["http.server.request"]), composable_always_on()),
                (AlwaysMatchPredicate(), composable_always_off()),
            ]
        )
    )

    matched = sampler.should_sample_span(
        None, RandomIdGenerator().generate_trace_id(), "GET /users", span_type="http.server.request"
    )
    unmatched = sampler.should_sample_span(
        None, RandomIdGenerator().generate_trace_id(), "GET /users", span_type="db.client.call"
    )

    assert matched.decision == Decision.RECORD_AND_SAMPLE
    assert unmatched.decision == Decision.DROP


class _LegacyComposableSampler:
    """Written against the protocol before span type existed."""

    def sampling_intent(self, parent_ctx, name, span_kind, attributes, links, trace_state):
        return SamplingIntent(threshold=0)

    def get_description(self):
        return "Legacy"


def test_predicate_and_sampler_without_span_type_keep_working():
    # NameIsFooPredicate also predates span type
    sampler = composite_sampler(composable_rule_based([(NameIsFooPredicate(), _LegacyComposableSampler())]))

    result = sampler.should_sample_span(
        None, RandomIdGenerator().generate_trace_id(), "foo", span_type="http.server.request"
    )

    assert result.decision == Decision.RECORD_AND_SAMPLE


class _RecordingPredicate:
    """Captures the keyword-only inputs the sampler was called with."""

    def __init__(self):
        self.calls = []

    def __call__(
        self,
        parent_ctx,
        name,
        span_kind,
        attributes,
        links,
        trace_state,
        *,
        span_type=None,
        instrumentation_scope=None,
        resource=None,
        **kwargs,
    ):
        self.calls.append((span_type, instrumentation_scope, resource))
        return True

    def __str__(self):
        return "Recording"


def test_scope_and_resource_reach_predicates_and_samplers():
    predicate = _RecordingPredicate()
    resource = Resource.create({"service.name": "test"})
    provider = TracerProvider(
        sampler=composite_sampler(composable_rule_based([(predicate, composable_always_on())])),
        resource=resource,
    )

    provider.get_tracer("my.library", "1.0").start_span("GET /users", span_type="http.server.request").end()

    assert len(predicate.calls) == 1
    span_type, scope, seen_resource = predicate.calls[0]
    assert span_type == "http.server.request"
    assert scope.name == "my.library"
    assert scope.version == "1.0"
    assert seen_resource is resource
