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

import dataclasses
import unittest


def _is_none_equivalent(val_a, val_b):
    """Check if two values should be treated as equal because one is None
    and the other is the empty/zero default for that type.

    Only None and type-matching empty defaults are considered equivalent:
      None == []   (empty list)
      None == ""   (empty string)
      None == b""  (empty bytes)
      None == 0    (zero int)
      None == 0.0  (zero float)
    """
    if val_a is None and val_b is None:
        return True
    if val_a is None:
        return val_b == type(val_b)()
    if val_b is None:
        return val_a == type(val_a)()
    return False


def assert_proto_json_equal(
    test_case: unittest.TestCase, obj_a, obj_b, path: str = ""
):
    """Recursively compare two proto_json dataclass objects, treating
    None as equivalent to the type's empty default ([], "", b"", 0, 0.0)."""
    if dataclasses.is_dataclass(obj_a) and dataclasses.is_dataclass(obj_b):
        for field in dataclasses.fields(obj_a):
            field_path = f"{path}.{field.name}" if path else field.name
            val_a = getattr(obj_a, field.name)
            val_b = getattr(obj_b, field.name)
            assert_proto_json_equal(test_case, val_a, val_b, field_path)
    elif isinstance(obj_a, list) and isinstance(obj_b, list):
        test_case.assertEqual(
            len(obj_a),
            len(obj_b),
            f"List length mismatch at {path}: {len(obj_a)} != {len(obj_b)}",
        )
        for i, (item_a, item_b) in enumerate(zip(obj_a, obj_b)):
            assert_proto_json_equal(test_case, item_a, item_b, f"{path}[{i}]")
    elif _is_none_equivalent(obj_a, obj_b):
        pass
    else:
        test_case.assertEqual(
            obj_a, obj_b, f"Mismatch at {path}: {obj_a!r} != {obj_b!r}"
        )
