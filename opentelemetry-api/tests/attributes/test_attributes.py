# type: ignore
import copy
import unittest
import unittest.mock
from typing import MutableSequence

from opentelemetry.attributes import (
    BoundedAttributes,
    _clean_attribute,
    _clean_extended_attribute,
    _clean_extended_attribute_value,
)


class TestAttributes(unittest.TestCase):
    def test_clean_attribute(self):
        self.assertEqual(_clean_attribute("key", "value", None), "value")
        self.assertEqual(_clean_attribute("key", 1, None), 1)
        self.assertEqual(_clean_attribute("key", 1.0, None), 1.0)
        self.assertEqual(_clean_attribute("key", True, None), True)
        self.assertEqual(_clean_attribute("key", b"value", None), None)
        self.assertEqual(
            _clean_attribute("key", ["a", "b"], None), ("a", "b")
        )
        self.assertEqual(
            _clean_attribute("key", ("a", "b"), None), ("a", "b")
        )
        self.assertEqual(
            _clean_attribute("key", ["a", 2, "b"], None), ("a", None, "b")
        )
        self.assertEqual(_clean_attribute("key", [], None), ())
        self.assertEqual(_clean_attribute("key", (), None), ())
        # Test max_value_len truncation
        self.assertEqual(_clean_attribute("key", "value", 3), "val")
        self.assertEqual(
            _clean_attribute("key", ["abc", "defg"], 3), ("abc", "def")
        )

    def test_clean_extended_attribute(self):
        self.assertIsNone(_clean_extended_attribute("key", object(), None))
        self.assertEqual(
            _clean_extended_attribute("key", "value", None), "value"
        )
        self.assertEqual(_clean_extended_attribute("key", 1, None), 1)
        self.assertEqual(_clean_extended_attribute("key", 1.0, None), 1.0)
        self.assertEqual(_clean_extended_attribute("key", True, None), True)
        self.assertEqual(
            _clean_extended_attribute("key", b"value", None), None
        )
        self.assertEqual(
            _clean_extended_attribute("key", ["a", "b"], None), ("a", "b")
        )
        self.assertEqual(
            _clean_extended_attribute("key", ("a", "b"), None), ("a", "b")
        )
        self.assertEqual(
            _clean_extended_attribute("key", [], None), ()
        )

    def test_clean_extended_attribute_with_wsgi_like_object(self):
        class DummyWSGIRequest:
            def __init__(self, method, path):
                self.method = method
                self.path = path

            def __str__(self):
                return f"<DummyWSGIRequest method={self.method} path={self.path}>"

        request = DummyWSGIRequest("GET", "/example/")
        cleaned_value = _clean_extended_attribute_value(request, None)
        self.assertEqual(
            "<DummyWSGIRequest method=GET path=/example/>", cleaned_value
        )

    def test_invalid_anyvalue_type_raises_typeerror(self):
        class BadStr:
            def __str__(self):
                raise Exception("boom")

        with self.assertRaises(TypeError):
            _clean_extended_attribute_value(BadStr(), None)


class TestBoundedAttributes(unittest.TestCase):
    base = {
        "name": "Alice",
        "age": 30,
        "height": 5.7,
        "active": True,
        "pets": ["dog", "cat"],
    }

    def test_negative_maxlen(self):
        with self.assertRaises(ValueError):
            BoundedAttributes(maxlen=-1)

    def test_from_map(self):
        bdict = BoundedAttributes(4, self.base)
        self.assertEqual(len(bdict), 4)
        for key in bdict:
            self.assertEqual(bdict[key], self.base[key])

    def test_bounded(self):
        bdict = BoundedAttributes(4, self.base)
        self.assertEqual(bdict.dropped, 1)

    def test_immutable(self):
        bdict = BoundedAttributes(4, self.base)
        with self.assertRaises(TypeError):
            bdict["name"] = "Bob"

    def test_mutable(self):
        bdict = BoundedAttributes(4, self.base, immutable=False)
        bdict["name"] = "Bob"
        self.assertEqual(bdict["name"], "Bob")

    def test_delete_immutable(self):
        bdict = BoundedAttributes(4, self.base)
        with self.assertRaises(TypeError):
            del bdict["name"]

    def test_no_limit(self):
        bdict = BoundedAttributes(attributes=self.base)
        self.assertEqual(len(bdict), len(self.base))

    def test_deepcopy(self):
        bdict = BoundedAttributes(4, self.base, immutable=False)
        bdict.dropped = 10
        bdict_copy = copy.deepcopy(bdict)
        for key in bdict_copy:
            self.assertEqual(bdict_copy[key], bdict[key])
        self.assertEqual(bdict_copy.dropped, bdict.dropped)
        self.assertEqual(bdict_copy.maxlen, bdict.maxlen)
        self.assertEqual(bdict_copy.max_value_len, bdict.max_value_len)
        bdict_copy["name"] = "Bob"
        self.assertNotEqual(bdict_copy["name"], bdict["name"])
        bdict["age"] = 99
        self.assertNotEqual(bdict["age"], bdict_copy["age"])

    def test_deepcopy_preserves_immutability(self):
        bdict = BoundedAttributes(
            maxlen=4, attributes=self.base, immutable=True
        )
        bdict_copy = copy.deepcopy(bdict)
        with self.assertRaises(TypeError):
            bdict_copy["invalid"] = "invalid"


if __name__ == "__main__":
    unittest.main()
