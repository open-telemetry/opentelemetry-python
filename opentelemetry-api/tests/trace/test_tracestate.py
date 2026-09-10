# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
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

    def test_tracestate_rejects_illegal_vendor_key(self):
        # Per W3C, the vendor part of a key (after '@') MUST be <= 13 chars.
        state = TraceState()
        # 14-char vendor is illegal and must be discarded.
        new_state = state.add("1@nrabcdefghijkl", "val")
        self.assertEqual(len(new_state), 0)
        self.assertIsNone(new_state.get("1@nrabcdefghijkl"))
        # long tenant with 14-char vendor is also illegal.
        new_state = state.add("12345678901234567890@nrabcdefghijkl", "val")
        self.assertEqual(len(new_state), 0)
        # a valid key (241-char tenant, 2-char vendor) is still accepted.
        valid_state = state.add("12345678901234567890@nr", "val")
        self.assertEqual(valid_state.get("12345678901234567890@nr"), "val")
        # a non-vendor key starting with a digit (no '@') is illegal.
        new_state = state.add("1acdfrgs", "val")
        self.assertEqual(len(new_state), 0)

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
