from unittest import TestCase
from unittest.mock import MagicMock

from opentelemetry.context import Context
from opentelemetry.sdk.trace._sampling_experimental import AlwaysRecordSampler
from opentelemetry.sdk.trace.sampling import (
    Decision,
    Sampler,
    SamplingResult,
    StaticSampler,
)
from opentelemetry.trace import SpanKind
from opentelemetry.trace.span import TraceState
from opentelemetry.util.types import Attributes


class TestAlwaysRecordSampler(TestCase):
    def setUp(self):
        self.mock_sampler: Sampler = MagicMock()
        self.sampler: Sampler = AlwaysRecordSampler(self.mock_sampler)

    def test_get_description(self):
        static_sampler: Sampler = StaticSampler(Decision.DROP)
        test_sampler: Sampler = AlwaysRecordSampler(static_sampler)
        self.assertEqual(
            "AlwaysRecordSampler{AlwaysOffSampler}",
            test_sampler.get_description(),
        )

    def test_record_and_sample_sampling_decision(self):
        self.validate_should_sample(
            Decision.RECORD_AND_SAMPLE, Decision.RECORD_AND_SAMPLE
        )

    def test_record_only_sampling_decision(self):
        self.validate_should_sample(Decision.RECORD_ONLY, Decision.RECORD_ONLY)

    def test_drop_sampling_decision(self):
        self.validate_should_sample(Decision.DROP, Decision.RECORD_ONLY)

    def validate_should_sample(
        self, root_decision: Decision, expected_decision: Decision
    ):
        root_result: SamplingResult = _build_root_sampling_result(
            root_decision
        )
        self.mock_sampler.should_sample.return_value = root_result
        actual_result: SamplingResult = self.sampler.should_sample(
            parent_context=Context(),
            trace_id=0,
            name="name",
            kind=SpanKind.CLIENT,
            attributes={"key": root_decision.name},
            trace_state=TraceState(),
        )

        if root_decision == expected_decision:
            self.assertEqual(actual_result, root_result)
            self.assertEqual(actual_result.decision, root_decision)
        else:
            self.assertNotEqual(actual_result, root_result)
            self.assertEqual(actual_result.decision, expected_decision)

        self.assertEqual(actual_result.attributes, root_result.attributes)
        self.assertEqual(actual_result.trace_state, root_result.trace_state)


def _build_root_sampling_result(sampling_decision: Decision):
    sampling_attr: Attributes = {"key": sampling_decision.name}
    sampling_trace_state: TraceState = TraceState()
    sampling_trace_state.add("key", sampling_decision.name)
    sampling_result: SamplingResult = SamplingResult(
        decision=sampling_decision,
        attributes=sampling_attr,
        trace_state=sampling_trace_state,
    )
    return sampling_result
