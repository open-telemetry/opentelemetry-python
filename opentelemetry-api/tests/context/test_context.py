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
from opentelemetry.context import Context, merge_context_correlation


class TestContext(unittest.TestCase):
    def test_merge(self):
        src_ctx = Context()
        src_ctx.contents = {
            "name": "first",
            "somebool": True,
            "key": "value",
            "otherkey": "othervalue",
        }
        dst_ctx = Context()
        dst_ctx.contents = {
            "name": "second",
            "somebool": False,
            "anotherkey": "anothervalue",
        }
        Context.set_current(merge_context_correlation(src_ctx, dst_ctx))
        expected = {
            "name": "first",
            "somebool": True,
            "key": "value",
            "otherkey": "othervalue",
            "anotherkey": "anothervalue",
        }
        self.assertEqual(expected, Context.current().contents)
