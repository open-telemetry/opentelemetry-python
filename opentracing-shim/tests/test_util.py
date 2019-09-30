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

import unittest

from opentracingshim import util


class TestUtil(unittest.TestCase):
    def test_event_name_from_kv(self):
        # Test basic behavior.
        event_name = "send HTTP request"
        res = util.event_name_from_kv({"event": event_name, "foo": "bar"})
        self.assertEqual(res, event_name)

        # Test None.
        res = util.event_name_from_kv(None)
        self.assertEqual(res, util.DEFAULT_EVENT_NAME)

        # Test empty dict.
        res = util.event_name_from_kv({})
        self.assertEqual(res, util.DEFAULT_EVENT_NAME)

        # Test missing `event` field.
        res = util.event_name_from_kv({"foo": "bar"})
        self.assertEqual(res, util.DEFAULT_EVENT_NAME)
