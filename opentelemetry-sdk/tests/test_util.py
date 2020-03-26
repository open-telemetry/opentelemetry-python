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

import collections
import unittest

from opentelemetry.sdk.util import BoundedDict, BoundedList


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
        with self.assertRaises(ValueError):
            BoundedList.from_seq(list_len / 2, self.base)

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


class TestBoundedDict(unittest.TestCase):
    base = collections.OrderedDict(
        [
            ("name", "Firulais"),
            ("age", 7),
            ("weight", 13),
            ("vaccinated", True),
        ]
    )

    def test_negative_maxlen(self):
        with self.assertRaises(ValueError):
            BoundedDict(-1)

    def test_from_map(self):
        dic_len = len(self.base)
        base_copy = collections.OrderedDict(self.base)
        bdict = BoundedDict.from_map(dic_len, base_copy)

        self.assertEqual(len(bdict), dic_len)

        # modify base_copy and test that bdict is not changed
        base_copy["name"] = "Bruno"
        base_copy["age"] = 3

        for key in self.base:
            self.assertEqual(bdict[key], self.base[key])

        # test that iter yields the correct number of elements
        self.assertEqual(len(tuple(bdict)), dic_len)

        # map too big
        with self.assertRaises(ValueError):
            BoundedDict.from_map(dic_len / 2, self.base)

    def test_bounded_dict(self):
        # create empty dict
        dic_len = len(self.base)
        bdict = BoundedDict(dic_len)
        self.assertEqual(len(bdict), 0)

        # fill dict
        for key in self.base:
            bdict[key] = self.base[key]

        self.assertEqual(len(bdict), dic_len)
        self.assertEqual(bdict.dropped, 0)

        for key in self.base:
            self.assertEqual(bdict[key], self.base[key])

        # test __iter__ in BoundedDict
        for key in bdict:
            self.assertEqual(bdict[key], self.base[key])

        # updating an existing element should not drop
        bdict["name"] = "Bruno"
        self.assertEqual(bdict.dropped, 0)

        # try to append more elements
        for key in self.base:
            bdict["new-" + key] = self.base[key]

        self.assertEqual(len(bdict), dic_len)
        self.assertEqual(bdict.dropped, dic_len)

        # test that elements in the dict are the new ones
        for key in self.base:
            self.assertEqual(bdict["new-" + key], self.base[key])

        # delete an element
        del bdict["new-name"]
        self.assertEqual(len(bdict), dic_len - 1)

        with self.assertRaises(KeyError):
            _ = bdict["new-name"]
