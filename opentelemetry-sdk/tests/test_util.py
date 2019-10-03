# Copyright 2019, OpenTelemetry Authors
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
        list_len = len(TestBoundedList.base)
        base_copy = list(TestBoundedList.base)
        blist = BoundedList.from_seq(list_len, base_copy)

        self.assertEqual(len(blist), list_len)

        # modify base_copy and test that blist is not changed
        for idx in range(list_len):
            base_copy[idx] = idx * base_copy[idx]

        for idx in range(list_len):
            self.assertEqual(blist[idx], TestBoundedList.base[idx])

        # test that iter yields the correct number of elements
        self.assertEqual(len(tuple(blist)), list_len)

        # sequence too big
        with self.assertRaises(ValueError):
            BoundedList.from_seq(list_len / 2, TestBoundedList.base)

    def test_append_no_drop(self):
        # create empty list
        list_len = len(TestBoundedList.base)
        blist = BoundedList(list_len)
        self.assertEqual(len(blist), 0)

        # fill list
        for item in TestBoundedList.base:
            blist.append(item)

        self.assertEqual(len(blist), list_len)
        self.assertEqual(blist.dropped, 0)

        for idx in range(list_len):
            self.assertEqual(blist[idx], TestBoundedList.base[idx])

        # test __iter__ in BoundedList
        idx = 0
        for val in blist:
            self.assertEqual(val, TestBoundedList.base[idx])
            idx += 1

    def test_append_drop(self):
        list_len = len(TestBoundedList.base)
        # create full BoundedList
        blist = BoundedList.from_seq(list_len, TestBoundedList.base)

        # try to append more items
        for idx in range(list_len):
            # should drop the element without raising exceptions
            blist.append(2 * TestBoundedList.base[idx])

        self.assertEqual(len(blist), list_len)
        self.assertEqual(blist.dropped, list_len)

        # test that new elements are in the list
        for idx in range(list_len):
            self.assertEqual(blist[idx], 2 * TestBoundedList.base[idx])

    def test_extend_no_drop(self):
        # create empty list
        list_len = len(TestBoundedList.base)
        blist = BoundedList(list_len)
        self.assertEqual(len(blist), 0)

        # fill list
        blist.extend(TestBoundedList.base)

        self.assertEqual(len(blist), list_len)
        self.assertEqual(blist.dropped, 0)

        for idx in range(list_len):
            self.assertEqual(blist[idx], TestBoundedList.base[idx])

        # test __iter__ in BoundedList
        idx = 0
        for val in blist:
            self.assertEqual(val, TestBoundedList.base[idx])
            idx += 1

    def test_extend_drop(self):
        list_len = len(TestBoundedList.base)
        # create full BoundedList
        blist = BoundedList.from_seq(list_len, TestBoundedList.base)
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
        dic_len = len(TestBoundedDict.base)
        base_copy = collections.OrderedDict(TestBoundedDict.base)
        bdict = BoundedDict.from_map(dic_len, base_copy)

        self.assertEqual(len(bdict), dic_len)

        # modify base_copy and test that bdict is not changed
        base_copy["name"] = "Bruno"
        base_copy["age"] = 3

        for key in TestBoundedDict.base:
            self.assertEqual(bdict[key], TestBoundedDict.base[key])

        # test that iter yields the correct number of elements
        self.assertEqual(len(tuple(bdict)), dic_len)

        # map too big
        with self.assertRaises(ValueError):
            BoundedDict.from_map(dic_len / 2, TestBoundedDict.base)

    def test_bounded_dict(self):
        # create empty dict
        dic_len = len(TestBoundedDict.base)
        bdict = BoundedDict(dic_len)
        self.assertEqual(len(bdict), 0)

        # fill dict
        for key in TestBoundedDict.base:
            bdict[key] = TestBoundedDict.base[key]

        self.assertEqual(len(bdict), dic_len)
        self.assertEqual(bdict.dropped, 0)

        for key in TestBoundedDict.base:
            self.assertEqual(bdict[key], TestBoundedDict.base[key])

        # test __iter__ in BoundedDict
        for key in bdict:
            self.assertEqual(bdict[key], TestBoundedDict.base[key])

        # updating an existing element should not drop
        bdict["name"] = "Bruno"
        self.assertEqual(bdict.dropped, 0)

        # try to append more elements
        for key in TestBoundedDict.base:
            bdict["new-" + key] = TestBoundedDict.base[key]

        self.assertEqual(len(bdict), dic_len)
        self.assertEqual(bdict.dropped, dic_len)

        # test that elements in the dict are the new ones
        for key in TestBoundedDict.base:
            self.assertEqual(bdict["new-" + key], TestBoundedDict.base[key])

        # delete an element
        del bdict["new-name"]
        self.assertEqual(len(bdict), dic_len - 1)

        with self.assertRaises(KeyError):
            _ = bdict["new-name"]
