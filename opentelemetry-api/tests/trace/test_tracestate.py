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

    def test_tracestate_update_new_key_added_below_capacity(self):
        # update() keeps its upsert behavior: a key that is not present is added
        # as long as there is room below the 32-entry limit.
        small_state = TraceState([("a", "1")])
        new_state = small_state.update("b", "2")
        self.assertEqual(new_state.get("b"), "2")
        self.assertEqual(new_state.get("a"), "1")

    def test_tracestate_update_at_capacity_new_key_preserved(self):
        # Guards the previous bug: adding a new key at the 32-entry limit used to
        # push the list to 33 entries and cause the constructor to wipe them all.
        # Now the tracestate is returned unchanged, preserving existing entries.
        pairs = [(f"key{i}", f"value{i}") for i in range(32)]
        state = TraceState(pairs)
        new_state = state.update("newkey", "newvalue")
        self.assertEqual(len(new_state), 32)
        self.assertIsNone(new_state.get("newkey"))
        self.assertEqual(new_state.get("key0"), "value0")

    def test_tracestate_update_existing_key_at_capacity(self):
        # Updating an existing key while at the limit stays within the limit.
        pairs = [(f"key{i}", f"value{i}") for i in range(32)]
        state = TraceState(pairs)
        new_state = state.update("key0", "changed")
        self.assertEqual(len(new_state), 32)
        self.assertEqual(new_state.get("key0"), "changed")

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
