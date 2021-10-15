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

import pickle
import unittest

from opentelemetry import trace


class TestSpanContext(unittest.TestCase):
    def test_span_context_pickle(self):
        """
        SpanContext needs to be pickleable to support multiprocessing
        so span can start as parent from the new spawned process
        """
        sc = trace.SpanContext(
            1,
            2,
            is_remote=False,
            trace_flags=trace.DEFAULT_TRACE_OPTIONS,
            trace_state=trace.DEFAULT_TRACE_STATE,
        )
        pickle_sc = pickle.loads(pickle.dumps(sc))
        self.assertEqual(sc.trace_id, pickle_sc.trace_id)
        self.assertEqual(sc.span_id, pickle_sc.span_id)

        invalid_sc = trace.SpanContext(
            9999999999999999999999999999999999999999999999999999999999999999999999999999,
            9,
            is_remote=False,
            trace_flags=trace.DEFAULT_TRACE_OPTIONS,
            trace_state=trace.DEFAULT_TRACE_STATE,
        )
        self.assertFalse(invalid_sc.is_valid)

    def test_trace_id_validity(self):
        trace_id_max_value = int("f" * 32, 16)
        span_id = 1

        # valid trace IDs
        sc = trace.SpanContext(trace_id_max_value, span_id, is_remote=False)
        self.assertTrue(sc.is_valid)

        sc = trace.SpanContext(1, span_id, is_remote=False)
        self.assertTrue(sc.is_valid)

        # invalid trace IDs
        sc = trace.SpanContext(0, span_id, is_remote=False)
        self.assertFalse(sc.is_valid)

        sc = trace.SpanContext(-1, span_id, is_remote=False)
        self.assertFalse(sc.is_valid)

        sc = trace.SpanContext(
            trace_id_max_value + 1, span_id, is_remote=False
        )
        self.assertFalse(sc.is_valid)

    def test_span_id_validity(self):
        span_id_max = int("f" * 16, 16)
        trace_id = 1

        # valid span IDs
        sc = trace.SpanContext(trace_id, span_id_max, is_remote=False)
        self.assertTrue(sc.is_valid)

        sc = trace.SpanContext(trace_id, 1, is_remote=False)
        self.assertTrue(sc.is_valid)

        # invalid span IDs
        sc = trace.SpanContext(trace_id, 0, is_remote=False)
        self.assertFalse(sc.is_valid)

        sc = trace.SpanContext(trace_id, -1, is_remote=False)
        self.assertFalse(sc.is_valid)

        sc = trace.SpanContext(trace_id, span_id_max + 1, is_remote=False)
        self.assertFalse(sc.is_valid)
