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
from unittest import TestCase

from opentelemetry.auto_instrumentation.instrumentor import BaseInstrumentor


class TestInstrumentor(TestCase):
    class Instrumentor(BaseInstrumentor):
        def _automatic_instrument(self):
            return "instrumented"

        def _automatic_uninstrument(self):
            return "uninstrumented"

        @BaseInstrumentor.protect_instrument
        def programmatic_instrument(self, arg):  # pylint: disable=no-self-use
            return "programmatically_instrumented {}".format(arg)

        @BaseInstrumentor.protect_uninstrument
        def programmatic_uninstrument(
            self, arg
        ):  # pylint: disable=no-self-use
            return "programmatically_uninstrumented {}".format(arg)

    def test_protect(self):
        instrumentor = self.Instrumentor()

        with self.assertLogs(level=WARNING):
            self.assertIs(instrumentor.automatic_uninstrument(), None)

        self.assertEqual(instrumentor.automatic_instrument(), "instrumented")
        with self.assertLogs(level=WARNING):
            self.assertIs(instrumentor.automatic_instrument(), None)

        self.assertEqual(
            instrumentor.automatic_uninstrument(), "uninstrumented"
        )

        with self.assertLogs(level=WARNING):
            self.assertIs(instrumentor.automatic_uninstrument(), None)

    def test_singleton(self):
        self.assertIs(self.Instrumentor(), self.Instrumentor())

    def test_protect_instrument_uninstrument(self):

        instrumentor = self.Instrumentor()

        with self.assertLogs(level=WARNING):
            self.assertIs(instrumentor.programmatic_uninstrument("test"), None)

        self.assertEqual(
            instrumentor.programmatic_instrument("test"),
            "programmatically_instrumented test",
        )

        with self.assertLogs(level=WARNING):
            self.assertIs(instrumentor.programmatic_instrument("test"), None)

        self.assertEqual(
            instrumentor.programmatic_uninstrument("test"),
            "programmatically_uninstrumented test",
        )

        with self.assertLogs(level=WARNING):
            self.assertIs(instrumentor.programmatic_uninstrument("test"), None)
