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

import unittest

from opentelemetry.util._patch import (
    _get_all_subclasses,
    _get_leaf_subclasses,
    patch_leaf_subclasses,
)


class TestPatchFunctionality(unittest.TestCase):
    """Test cases for the patching functionality in _patch.py"""

    def setUp(self):
        """Set up test classes for each test case"""
        # Create a fresh set of test classes for each test
        # to avoid interference between tests

        class BaseClass:
            def target_method(self):
                return "base"

            def other_method(self):
                return "base_other"

        class IntermediateClass(BaseClass):
            def target_method(self):
                return "intermediate"

        class LeafClass1(IntermediateClass):
            def target_method(self):
                return "leaf1"

        class LeafClass2(IntermediateClass):
            def target_method(self):
                return "leaf2"

        class LeafClass3(BaseClass):
            def target_method(self):
                return "leaf3"

        class LeafClassWithoutMethod(BaseClass):
            pass  # Inherits target_method from BaseClass

        class LeafClassWithNonCallable(BaseClass):
            target_method = "not_callable"

        self.BaseClass = BaseClass
        self.IntermediateClass = IntermediateClass
        self.LeafClass1 = LeafClass1
        self.LeafClass2 = LeafClass2
        self.LeafClass3 = LeafClass3
        self.LeafClassWithoutMethod = LeafClassWithoutMethod
        self.LeafClassWithNonCallable = LeafClassWithNonCallable

    def test_get_all_subclasses_single_level(self):
        """Test _get_all_subclasses with single inheritance level"""
        subclasses = _get_all_subclasses(self.BaseClass)
        expected_subclasses = {
            self.IntermediateClass,
            self.LeafClass1,
            self.LeafClass2,
            self.LeafClass3,
            self.LeafClassWithoutMethod,
            self.LeafClassWithNonCallable,
        }
        self.assertEqual(subclasses, expected_subclasses)

    def test_get_all_subclasses_intermediate_class(self):
        """Test _get_all_subclasses with intermediate class"""
        subclasses = _get_all_subclasses(self.IntermediateClass)
        expected_subclasses = {self.LeafClass1, self.LeafClass2}
        self.assertEqual(subclasses, expected_subclasses)

    def test_get_all_subclasses_leaf_class(self):
        """Test _get_all_subclasses with leaf class (no subclasses)"""
        subclasses = _get_all_subclasses(self.LeafClass1)
        self.assertEqual(subclasses, set())

    def test_get_leaf_subclasses(self):
        """Test _get_leaf_subclasses correctly identifies leaf classes"""
        all_subclasses = _get_all_subclasses(self.BaseClass)
        leaf_subclasses = _get_leaf_subclasses(all_subclasses)

        expected_leaf_classes = {
            self.LeafClass1,
            self.LeafClass2,
            self.LeafClass3,
            self.LeafClassWithoutMethod,
            self.LeafClassWithNonCallable,
        }
        self.assertEqual(leaf_subclasses, expected_leaf_classes)

    def test_get_leaf_subclasses_empty_set(self):
        """Test _get_leaf_subclasses with empty set"""
        leaf_subclasses = _get_leaf_subclasses(set())
        self.assertEqual(leaf_subclasses, set())

    def test_get_leaf_subclasses_single_class(self):
        """Test _get_leaf_subclasses with single class"""
        leaf_subclasses = _get_leaf_subclasses({self.LeafClass1})
        self.assertEqual(leaf_subclasses, {self.LeafClass1})

    def test_patch_leaf_subclasses_basic(self):
        """Test basic patching functionality"""
        call_tracker = []

        def wrapper(original_method):
            def wrapped(*args, **kwargs):
                call_tracker.append(f"wrapped_{original_method.__name__}")
                res = original_method(*args, **kwargs)
                return f"wrapped_{res}"

            return wrapped

        # Apply patch
        patch_leaf_subclasses(self.BaseClass, "target_method", wrapper)

        # Test that leaf classes are patched
        leaf1_instance = self.LeafClass1()
        leaf2_instance = self.LeafClass2()
        leaf3_instance = self.LeafClass3()
        leaf_without_method_instance = self.LeafClassWithoutMethod()

        # Check results
        self.assertEqual(leaf1_instance.target_method(), "wrapped_leaf1")
        self.assertEqual(leaf2_instance.target_method(), "wrapped_leaf2")
        self.assertEqual(leaf3_instance.target_method(), "wrapped_leaf3")
        self.assertEqual(
            leaf_without_method_instance.target_method(), "wrapped_base"
        )

        # Check that wrapper was called
        expected_calls = ["wrapped_target_method"] * 4
        self.assertEqual(call_tracker, expected_calls)

        # Test that intermediate class is NOT patched
        intermediate_instance = self.IntermediateClass()
        call_tracker.clear()
        result = intermediate_instance.target_method()
        self.assertEqual(result, "intermediate")
        self.assertEqual(call_tracker, [])  # No wrapper calls

    def test_patch_leaf_subclasses_non_callable_attribute(self):
        """Test that non-callable attributes are not patched"""

        def wrapper(original_method):
            def wrapped(*args, **kwargs):
                return "wrapped"

            return wrapped

        # Apply patch
        patch_leaf_subclasses(self.BaseClass, "target_method", wrapper)

        # Test that class with non-callable attribute is not patched
        leaf_non_callable_instance = self.LeafClassWithNonCallable()
        self.assertEqual(
            leaf_non_callable_instance.target_method, "not_callable"
        )

    def test_patch_leaf_subclasses_nonexistent_method(self):
        """Test patching a method that doesn't exist"""

        def wrapper(original_method):
            def wrapped(*args, **kwargs):
                return "wrapped"

            return wrapped

        # This should not raise an exception
        patch_leaf_subclasses(self.BaseClass, "nonexistent_method", wrapper)

        # Verify that instances still work normally
        leaf1_instance = self.LeafClass1()
        self.assertEqual(leaf1_instance.target_method(), "leaf1")

    def test_patch_leaf_subclasses_preserves_original_behavior(self):
        """Test that patching preserves the original method behavior"""

        def identity_wrapper(original_method):
            def wrapped(*args, **kwargs):
                return original_method(*args, **kwargs)

            return wrapped

        # Apply patch
        patch_leaf_subclasses(
            self.BaseClass, "target_method", identity_wrapper
        )

        # Test that behavior is preserved
        leaf1_instance = self.LeafClass1()
        leaf2_instance = self.LeafClass2()

        self.assertEqual(leaf1_instance.target_method(), "leaf1")
        self.assertEqual(leaf2_instance.target_method(), "leaf2")

    def test_patch_leaf_subclasses_with_arguments(self):
        """Test patching methods that take arguments"""

        class TestClassWithArgs:
            def method_with_args(self, x, y=10):
                return x + y

        class ChildClass(TestClassWithArgs):
            def method_with_args(self, x, y=20):
                return x * y

        def arg_tracking_wrapper(original_method):
            def wrapped(*args, **kwargs):
                # Track that we're in the wrapper and call original
                result = original_method(*args, **kwargs)
                return result + 1000  # Add marker to show wrapping occurred

            return wrapped

        patch_leaf_subclasses(
            TestClassWithArgs, "method_with_args", arg_tracking_wrapper
        )

        child_instance = ChildClass()
        result = child_instance.method_with_args(5, y=3)
        self.assertEqual(result, 1015)  # (5 * 3) + 1000

    def test_patch_leaf_subclasses_multiple_methods(self):
        """Test patching multiple different methods"""
        call_tracker = []

        def wrapper(original_method):
            def wrapped(*args, **kwargs):
                call_tracker.append(f"wrapped_{original_method.__name__}")
                return original_method(*args, **kwargs)

            return wrapped

        # Patch different methods
        patch_leaf_subclasses(self.BaseClass, "target_method", wrapper)
        patch_leaf_subclasses(self.BaseClass, "other_method", wrapper)

        # Test both methods are patched
        leaf1_instance = self.LeafClass1()
        leaf1_instance.target_method()
        leaf1_instance.other_method()

        self.assertIn("wrapped_target_method", call_tracker)
        self.assertIn("wrapped_other_method", call_tracker)

    def test_complex_inheritance_hierarchy(self):
        """Test with a more complex inheritance hierarchy"""

        class A:
            def method(self):
                return "A"

        class B(A):
            def method(self):
                return "B"

        class C(A):
            def method(self):
                return "C"

        class D(B):
            def method(self):
                return "D"

        class E(B):
            pass  # Inherits from B

        class F(C):
            def method(self):
                return "F"

        def wrapper(original_method):
            def wrapped(*args, **kwargs):
                result = original_method(*args, **kwargs)
                return f"wrapped_{result}"

            return wrapped

        patch_leaf_subclasses(A, "method", wrapper)

        # Test leaf classes are patched
        d_instance = D()
        e_instance = E()
        f_instance = F()

        self.assertEqual(d_instance.method(), "wrapped_D")
        self.assertEqual(e_instance.method(), "wrapped_B")  # Inherits from B
        self.assertEqual(f_instance.method(), "wrapped_F")

        # Test intermediate classes are not patched
        b_instance = B()
        c_instance = C()

        self.assertEqual(b_instance.method(), "B")
        self.assertEqual(c_instance.method(), "C")


if __name__ == "__main__":
    unittest.main()
