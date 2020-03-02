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

import os
import sys
import unittest
from importlib import reload
from typing import Any, Callable

from opentelemetry import trace
from opentelemetry.util import loader

DUMMY_TRACER_PROVIDER = None


class DummyTracerProvider(trace.TracerProvider):
    def get_tracer(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str = "",
    ) -> "trace.Tracer":
        return trace.DefaultTracer()


def get_opentelemetry_implementation(type_):
    global DUMMY_TRACER_PROVIDER  # pylint:disable=global-statement
    assert type_ is trace.TracerProvider
    DUMMY_TRACER_PROVIDER = DummyTracerProvider()
    return DUMMY_TRACER_PROVIDER


# pylint:disable=redefined-outer-name,protected-access,unidiomatic-typecheck


class TestLoader(unittest.TestCase):
    def setUp(self):
        reload(loader)
        reload(trace)

        # Need to reload self, otherwise DummyTracerProvider will have the wrong
        # base class after reloading `trace`.
        reload(sys.modules[__name__])

    def test_get_default(self):
        tracer_provider = trace.tracer_provider()
        self.assertIs(type(tracer_provider), trace.DefaultTracerProvider)

    def test_preferred_impl(self):
        trace.set_preferred_tracer_provider_implementation(
            get_opentelemetry_implementation
        )
        tracer_provider = trace.tracer_provider()
        self.assertIs(tracer_provider, DUMMY_TRACER_PROVIDER)

    # NOTE: We use do_* + *_<arg> methods because subtest wouldn't run setUp,
    # which we require here.
    def do_test_preferred_impl(self, setter: Callable[[Any], Any]) -> None:
        setter(get_opentelemetry_implementation)
        tracer_provider = trace.tracer_provider()
        self.assertIs(tracer_provider, DUMMY_TRACER_PROVIDER)

    def test_preferred_impl_with_tracer(self):
        self.do_test_preferred_impl(
            trace.set_preferred_tracer_provider_implementation
        )

    def test_preferred_impl_with_default(self):
        self.do_test_preferred_impl(
            loader.set_preferred_default_implementation
        )

    def test_try_set_again(self):
        self.assertTrue(trace.tracer_provider())
        # Try setting after the tracer_provider has already been created:
        with self.assertRaises(RuntimeError) as einfo:
            trace.set_preferred_tracer_provider_implementation(
                get_opentelemetry_implementation
            )
        self.assertIn("already loaded", str(einfo.exception))

    def do_test_get_envvar(self, envvar_suffix: str) -> None:
        global DUMMY_TRACER_PROVIDER  # pylint:disable=global-statement

        # Test is not runnable with this!
        self.assertFalse(sys.flags.ignore_environment)

        envname = "OPENTELEMETRY_PYTHON_IMPLEMENTATION_" + envvar_suffix
        os.environ[envname] = __name__
        try:
            tracer_provider = trace.tracer_provider()
            self.assertIs(tracer_provider, DUMMY_TRACER_PROVIDER)
        finally:
            DUMMY_TRACER_PROVIDER = None
            del os.environ[envname]
        self.assertIs(type(tracer_provider), DummyTracerProvider)

    def test_get_envvar_tracer(self):
        return self.do_test_get_envvar("TRACERPROVIDER")

    def test_get_envvar_default(self):
        return self.do_test_get_envvar("DEFAULT")
