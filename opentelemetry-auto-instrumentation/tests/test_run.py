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
# type: ignore

from os import environ
from os.path import abspath, dirname, pathsep
from unittest import TestCase
from unittest.mock import patch

from opentelemetry.auto_instrumentation import auto_instrumentation


class TestRun(TestCase):
    auto_instrumentation_path = dirname(abspath(auto_instrumentation.__file__))

    @classmethod
    def setUpClass(cls):
        cls.argv_patcher = patch(
            "opentelemetry.auto_instrumentation.auto_instrumentation.argv"
        )
        cls.execl_patcher = patch(
            "opentelemetry.auto_instrumentation.auto_instrumentation.execl"
        )
        cls.which_patcher = patch(
            "opentelemetry.auto_instrumentation.auto_instrumentation.which"
        )

        cls.argv_patcher.start()
        cls.execl_patcher.start()
        cls.which_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.argv_patcher.stop()
        cls.execl_patcher.stop()
        cls.which_patcher.stop()

    @patch.dict("os.environ", {"PYTHONPATH": ""})
    def test_empty(self):
        auto_instrumentation.run()
        self.assertEqual(environ["PYTHONPATH"], self.auto_instrumentation_path)

    @patch.dict("os.environ", {"PYTHONPATH": "abc"})
    def test_non_empty(self):
        auto_instrumentation.run()
        self.assertEqual(
            environ["PYTHONPATH"],
            pathsep.join([self.auto_instrumentation_path, "abc"]),
        )

    @patch.dict(
        "os.environ",
        {"PYTHONPATH": pathsep.join(["abc", auto_instrumentation_path])},
    )
    def test_after_path(self):
        auto_instrumentation.run()
        self.assertEqual(
            environ["PYTHONPATH"],
            pathsep.join([self.auto_instrumentation_path, "abc"]),
        )

    @patch.dict(
        "os.environ",
        {
            "PYTHONPATH": pathsep.join(
                [auto_instrumentation_path, "abc", auto_instrumentation_path]
            )
        },
    )
    def test_single_path(self):
        auto_instrumentation.run()
        self.assertEqual(
            environ["PYTHONPATH"],
            pathsep.join([self.auto_instrumentation_path, "abc"]),
        )
