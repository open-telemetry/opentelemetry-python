# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# type: ignore

from re import fullmatch
from unittest import TestCase

from opentelemetry.baggage import (
    _KEY_CHARS,
    _VALUE_CHARS,
    _is_valid_key,
    _is_valid_value,
    clear,
    get_all,
    get_baggage,
    remove_baggage,
    set_baggage,
)
from opentelemetry.context import attach, detach
from opentelemetry.util.re import _KEY_FORMAT, _VALUE_FORMAT


class TestBaggageManager(TestCase):
    def test_set_baggage(self):
        self.assertEqual({}, get_all())

        ctx = set_baggage("test", "value")
        self.assertEqual(get_baggage("test", context=ctx), "value")

        ctx = set_baggage("test", "value2", context=ctx)
        self.assertEqual(get_baggage("test", context=ctx), "value2")

    def test_baggages_current_context(self):
        token = attach(set_baggage("test", "value"))
        self.assertEqual(get_baggage("test"), "value")
        detach(token)
        self.assertEqual(get_baggage("test"), None)

    def test_set_multiple_baggage_entries(self):
        ctx = set_baggage("test", "value")
        ctx = set_baggage("test2", "value2", context=ctx)
        self.assertEqual(get_baggage("test", context=ctx), "value")
        self.assertEqual(get_baggage("test2", context=ctx), "value2")
        self.assertEqual(
            get_all(context=ctx),
            {"test": "value", "test2": "value2"},
        )

    def test_modifying_baggage(self):
        ctx = set_baggage("test", "value")
        self.assertEqual(get_baggage("test", context=ctx), "value")
        baggage_entries = get_all(context=ctx)
        with self.assertRaises(TypeError):
            baggage_entries["test"] = "mess-this-up"
        self.assertEqual(get_baggage("test", context=ctx), "value")

    def test_remove_baggage_entry(self):
        self.assertEqual({}, get_all())

        ctx = set_baggage("test", "value")
        ctx = set_baggage("test2", "value2", context=ctx)
        ctx = remove_baggage("test", context=ctx)
        self.assertEqual(get_baggage("test", context=ctx), None)
        self.assertEqual(get_baggage("test2", context=ctx), "value2")

    def test_clear_baggage(self):
        self.assertEqual({}, get_all())

        ctx = set_baggage("test", "value")
        self.assertEqual(get_baggage("test", context=ctx), "value")

        ctx = clear(context=ctx)
        self.assertEqual(get_all(context=ctx), {})

    def test_is_valid_value(self):
        for value, expected in (
            ("GET%20%2Fapi%2F%2Freport", True),
            ("val1 ;prop=1", True),
            ("val1\t; p1 = 1 ; p2", True),
            ("val 1;prop", False),
            ("", True),
            ("val1;", False),
            ("val1; ", False),
            ("val1;prop=a=b", True),
            ("val1;prop=", True),
            ("val1;=1", False),
            ("val1;pr op=1", False),
            ("val1;prop=a b", False),
            ('val"1', False),
            ("val\\1", False),
            ("val,1", False),
            ("val\x7f1", False),
            ("val\u00e91", False),
        ):
            with self.subTest(value=value):
                self.assertEqual(_is_valid_value(value), expected)

    def test_is_valid_key(self):
        for key, expected in (
            ("key1", True),
            ("!#$%&'*+-.^_`|~", True),
            ("", False),
            ("key 1", False),
            ("key=1", False),
            ("key\u00e9", False),
        ):
            with self.subTest(key=key):
                self.assertEqual(_is_valid_key(key), expected)

    def test_valid_characters_match_formats(self):
        chars = [chr(code_point) for code_point in range(0x100)]
        self.assertEqual(_KEY_CHARS, {char for char in chars if fullmatch(_KEY_FORMAT, char)})
        self.assertEqual(_VALUE_CHARS, {char for char in chars if fullmatch(_VALUE_FORMAT, char)})
