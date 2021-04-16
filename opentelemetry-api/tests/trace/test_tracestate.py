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
# pylint: disable=no-member

import unittest

from opentelemetry.trace.span import TraceState


class TestTraceContextFormat(unittest.TestCase):
    def test_empty_tracestate(self):
        state = TraceState()
        self.assertEqual(len(state), 0)
        self.assertEqual(state.to_header(), "")

    def test_tracestate_valid_pairs(self):
        pairs = [("1a-2f@foo", "bar1"), ("foo-_*/bar", "bar4")]
        state = TraceState(pairs)
        self.assertEqual(len(state), 2)
        self.assertIsNotNone(state.get("foo-_*/bar"))
        self.assertEqual(state.get("foo-_*/bar"), "bar4")
        self.assertEqual(state.to_header(), "1a-2f@foo=bar1,foo-_*/bar=bar4")
        self.assertIsNone(state.get("random"))

    def test_tracestate_add_valid(self):
        state = TraceState()
        new_state = state.add("1a-2f@foo", "bar4")
        self.assertEqual(len(new_state), 1)
        self.assertEqual(new_state.get("1a-2f@foo"), "bar4")

    def test_tracestate_add_invalid(self):
        state = TraceState()
        new_state = state.add("%%%nsasa", "val")
        self.assertEqual(len(new_state), 0)
        new_state = new_state.add("key", "====val====")
        self.assertEqual(len(new_state), 0)
        self.assertEqual(new_state.to_header(), "")

    def test_tracestate_update_valid(self):
        state = TraceState([("a", "1")])
        new_state = state.update("a", "2")
        self.assertEqual(new_state.get("a"), "2")
        new_state = new_state.add("b", "3")
        self.assertNotEqual(state, new_state)

    def test_tracestate_update_invalid(self):
        state = TraceState([("a", "1")])
        new_state = state.update("a", "2=/")
        self.assertNotEqual(new_state.get("a"), "2=/")
        new_state = new_state.update("a", ",,2,,f")
        self.assertNotEqual(new_state.get("a"), ",,2,,f")
        self.assertEqual(new_state.get("a"), "1")

    def test_tracestate_delete_preserved(self):
        state = TraceState([("a", "1"), ("b", "2"), ("c", "3")])
        new_state = state.delete("b")
        self.assertIsNone(new_state.get("b"))
        entries = list(new_state.items())
        a_place = entries.index(("a", "1"))
        c_place = entries.index(("c", "3"))
        self.assertLessEqual(a_place, c_place)

    def test_tracestate_from_header(self):
        entries = [
            "1a-2f@foo=bar1",
            "1a-_*/2b@foo=bar2",
            "foo=bar3",
            "foo-_*/bar=bar4",
        ]
        header_list = [",".join(entries)]
        state = TraceState.from_header(header_list)
        self.assertEqual(state.to_header(), ",".join(entries))

    def test_tracestate_order_changed(self):
        entries = [
            "1a-2f@foo=bar1",
            "1a-_*/2b@foo=bar2",
            "foo=bar3",
            "foo-_*/bar=bar4",
        ]
        header_list = [",".join(entries)]
        state = TraceState.from_header(header_list)
        new_state = state.update("foo", "bar33")
        entries = list(new_state.items())  # type: ignore
        foo_place = entries.index(("foo", "bar33"))  # type: ignore
        prev_first_place = entries.index(("1a-2f@foo", "bar1"))  # type: ignore
        self.assertLessEqual(foo_place, prev_first_place)

    def test_trace_contains(self):
        entries = [
            "1a-2f@foo=bar1",
            "1a-_*/2b@foo=bar2",
            "foo=bar3",
            "foo-_*/bar=bar4",
        ]
        header_list = [",".join(entries)]
        state = TraceState.from_header(header_list)

        self.assertTrue("foo" in state)
        self.assertFalse("bar" in state)
        self.assertIsNone(state.get("bar"))
        with self.assertRaises(KeyError):
            state["bar"]  # pylint:disable=W0104
