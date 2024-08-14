from unittest import TestCase

from opentelemetry.context import Context
from opentelemetry.sdk.metrics._internal.exemplar import (
    AlwaysOffExemplarFilter,
    AlwaysOnExemplarFilter,
    TraceBasedExemplarFilter,
)


class TestAlwaysOnExemplarFilter(TestCase):
    def test_should_sample(self):
        filter = AlwaysOnExemplarFilter()
        self.assertTrue(filter.should_sample(10, 0, {}, Context()))


class TestAlwaysOffExemplarFilter(TestCase):
    def test_should_sample(self):
        filter = AlwaysOffExemplarFilter()
        self.assertFalse(filter.should_sample(10, 0, {}, Context()))


class TestTraceBasedExemplarFilter(TestCase):
    def test_should_not_sample_without_trace(self):
        filter = TraceBasedExemplarFilter()
        self.assertFalse(filter.should_sample(10, 0, {}, Context()))

        # FIXME add test with trace that should sample
