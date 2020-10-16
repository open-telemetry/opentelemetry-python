import unittest

import opentelemetry.trace as trace_api


# pylint: disable=C0103
class OpenTelemetryTestCase(unittest.TestCase):
    def assertSameTrace(self, spanA, spanB):
        return self.assertEqual(
            spanA.get_span_reference().trace_id,
            spanB.get_span_reference().trace_id,
        )

    def assertNotSameTrace(self, spanA, spanB):
        return self.assertNotEqual(
            spanA.get_span_reference().trace_id,
            spanB.get_span_reference().trace_id,
        )

    def assertIsChildOf(self, spanA, spanB):
        # spanA is child of spanB
        self.assertIsNotNone(spanA.parent)

        refA = spanA.parent
        if isinstance(refA, trace_api.Span):
            refA = spanA.parent.get_span_reference()

        refB = spanB
        if isinstance(refB, trace_api.Span):
            refB = spanB.get_span_reference()

        return self.assertEqual(refA.span_id, refB.span_id)

    def assertIsNotChildOf(self, spanA, spanB):
        # spanA is NOT child of spanB
        if spanA.parent is None:
            return

        refA = spanA.parent
        if isinstance(refA, trace_api.Span):
            refA = spanA.parent.get_span_reference()

        refB = spanB
        if isinstance(refB, trace_api.Span):
            refB = spanB.get_span_reference()

        self.assertNotEqual(refA.span_id, refB.span_id)

    def assertNamesEqual(self, spans, names):
        self.assertEqual(list(map(lambda x: x.name, spans)), names)
