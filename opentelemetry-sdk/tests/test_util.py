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

from opentelemetry.sdk.util import BoundedList


# pylint: disable=unsubscriptable-object
class TestBoundedList(unittest.TestCase):
    base = [52, 36, 53, 29, 54, 99, 56, 48, 22, 35, 21, 65, 10, 95, 42, 60]

    def test_raises(self):
        """Test corner cases

        - negative list size
        - access out of range indexes
        """
        with self.assertRaises(ValueError):
            BoundedList(-1)

        blist = BoundedList(4)
        blist.append(37)
        blist.append(13)

        with self.assertRaises(IndexError):
            _ = blist[2]

        with self.assertRaises(IndexError):
            _ = blist[4]

        with self.assertRaises(IndexError):
            _ = blist[-3]

    def test_from_seq(self):
        list_len = len(self.base)
        base_copy = list(self.base)
        blist = BoundedList.from_seq(list_len, base_copy)

        self.assertEqual(len(blist), list_len)

        # modify base_copy and test that blist is not changed
        for idx in range(list_len):
            base_copy[idx] = idx * base_copy[idx]

        for idx in range(list_len):
            self.assertEqual(blist[idx], self.base[idx])

        # test that iter yields the correct number of elements
        self.assertEqual(len(tuple(blist)), list_len)

        # sequence too big
        blist = BoundedList.from_seq(list_len // 2, base_copy)
        self.assertEqual(len(blist), list_len // 2)
        self.assertEqual(blist.dropped, list_len - (list_len // 2))

    def test_append_no_drop(self):
        """Append max capacity elements to the list without dropping elements."""
        # create empty list
        list_len = len(self.base)
        blist = BoundedList(list_len)
        self.assertEqual(len(blist), 0)

        # fill list
        for item in self.base:
            blist.append(item)

        self.assertEqual(len(blist), list_len)
        self.assertEqual(blist.dropped, 0)

        for idx in range(list_len):
            self.assertEqual(blist[idx], self.base[idx])

        # test __iter__ in BoundedList
        for idx, val in enumerate(blist):
            self.assertEqual(val, self.base[idx])

    def test_append_drop(self):
        """Append more than max capacity elements and test that oldest ones are dropped."""
        list_len = len(self.base)
        # create full BoundedList
        blist = BoundedList.from_seq(list_len, self.base)

        # try to append more items
        for val in self.base:
            # should drop the element without raising exceptions
            blist.append(2 * val)

        self.assertEqual(len(blist), list_len)
        self.assertEqual(blist.dropped, list_len)

        # test that new elements are in the list
        for idx in range(list_len):
            self.assertEqual(blist[idx], 2 * self.base[idx])

    def test_extend_no_drop(self):
        # create empty list
        list_len = len(self.base)
        blist = BoundedList(list_len)
        self.assertEqual(len(blist), 0)

        # fill list
        blist.extend(self.base)

        self.assertEqual(len(blist), list_len)
        self.assertEqual(blist.dropped, 0)

        for idx in range(list_len):
            self.assertEqual(blist[idx], self.base[idx])

        # test __iter__ in BoundedList
        for idx, val in enumerate(blist):
            self.assertEqual(val, self.base[idx])

    def test_extend_drop(self):
        list_len = len(self.base)
        # create full BoundedList
        blist = BoundedList.from_seq(list_len, self.base)
        other_list = [13, 37, 51, 91]

        # try to extend with more elements
        blist.extend(other_list)

        self.assertEqual(len(blist), list_len)
        self.assertEqual(blist.dropped, len(other_list))

    def test_no_limit(self):
        blist = BoundedList(maxlen=None)
        for num in range(100):
            blist.append(num)

        for num in range(100):
            self.assertEqual(blist[num], num)
