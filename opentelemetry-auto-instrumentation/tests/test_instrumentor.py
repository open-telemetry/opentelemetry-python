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

from logging import WARNING
from os import environ
from os.path import abspath, dirname, pathsep
from unittest import TestCase
from unittest.mock import patch

from opentelemetry.auto_instrumentation import auto_instrumentation
from opentelemetry.auto_instrumentation.instrumentor import BaseInstrumentor


class TestInstrumentor(TestCase):
    class Instrumentor(BaseInstrumentor):
        def _instrument(self, **kwargs):
            return "instrumented"

        def _uninstrument(self, **kwargs):
            return "uninstrumented"

    def test_protect(self):
        instrumentor = self.Instrumentor()

        with self.assertLogs(level=WARNING):
            self.assertIs(instrumentor.uninstrument(), None)

        self.assertEqual(instrumentor.instrument(), "instrumented")

        with self.assertLogs(level=WARNING):
            self.assertIs(instrumentor.instrument(), None)

        self.assertEqual(instrumentor.uninstrument(), "uninstrumented")

        with self.assertLogs(level=WARNING):
            self.assertIs(instrumentor.uninstrument(), None)

    def test_singleton(self):
        self.assertIs(self.Instrumentor(), self.Instrumentor())


class TestRun(TestCase):
    auto_instrumentation_path = dirname(abspath(auto_instrumentation.__file__))

    @patch.dict("os.environ", {"PYTHONPATH": ""})
    @patch("opentelemetry.auto_instrumentation.auto_instrumentation.argv")
    @patch("opentelemetry.auto_instrumentation.auto_instrumentation.execl")
    def test_run_empty(
        self, mock_execl, mock_argv
    ):  # pylint: disable=unused-argument
        auto_instrumentation.run()
        assert environ["PYTHONPATH"] == self.auto_instrumentation_path

    @patch.dict("os.environ", {"PYTHONPATH": "abc"})
    @patch("opentelemetry.auto_instrumentation.auto_instrumentation.argv")
    @patch("opentelemetry.auto_instrumentation.auto_instrumentation.execl")
    def test_run_non_empty(
        self, mock_execl, mock_argv
    ):  # pylint: disable=unused-argument
        auto_instrumentation.run()
        assert environ["PYTHONPATH"] == pathsep.join(
            [self.auto_instrumentation_path, "abc"]
        )

    @patch.dict(
        "os.environ",
        {"PYTHONPATH": pathsep.join(["abc", auto_instrumentation_path])},
    )
    @patch("opentelemetry.auto_instrumentation.auto_instrumentation.argv")
    @patch("opentelemetry.auto_instrumentation.auto_instrumentation.execl")
    def test_run_after_path(
        self, mock_execl, mock_argv
    ):  # pylint: disable=unused-argument
        auto_instrumentation.run()
        assert environ["PYTHONPATH"] == pathsep.join(
            [self.auto_instrumentation_path, "abc"]
        )
