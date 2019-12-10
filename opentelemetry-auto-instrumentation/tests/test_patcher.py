# Copyright 2020, OpenTelemetry Authors
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
# type: ignore

from logging import WARNING
from unittest import TestCase

from opentelemetry.auto_instrumentation.patcher import BasePatcher


class TestPatcher(TestCase):
    def test_protect(self):
        class Patcher(BasePatcher):
            def _patch(self):
                return "patched"

            def _unpatch(self):
                return "unpatched"

        patcher = Patcher()

        with self.assertLogs(level=WARNING):
            self.assertIs(patcher.unpatch(), None)

        self.assertEqual(patcher.patch(), "patched")

        with self.assertLogs(level=WARNING):
            self.assertIs(patcher.patch(), None)

        self.assertEqual(patcher.unpatch(), "unpatched")

        with self.assertLogs(level=WARNING):
            self.assertIs(patcher.unpatch(), None)
