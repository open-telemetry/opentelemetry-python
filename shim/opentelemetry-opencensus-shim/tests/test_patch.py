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

from opencensus.trace.tracer import Tracer
from opencensus.trace.tracers.noop_tracer import NoopTracer

from opentelemetry.shim.opencensus import install_shim, uninstall_shim
from opentelemetry.shim.opencensus._shim_tracer import ShimTracer


class TestPatch(unittest.TestCase):
    def setUp(self):
        uninstall_shim()

    def tearDown(self):
        uninstall_shim()

    def test_install_shim(self):
        # Initially the shim is not installed. The Tracer class has no tracer property, it is
        # instance level only.
        self.assertFalse(hasattr(Tracer, "tracer"))

        install_shim()

        # The actual Tracer class should now be patched with a tracer property
        self.assertTrue(hasattr(Tracer, "tracer"))
        self.assertIsInstance(Tracer.tracer, property)

    def test_install_shim_affects_existing_tracers(self):
        # Initially the shim is not installed. A OC Tracer instance should have a NoopTracer
        oc_tracer = Tracer()
        self.assertIsInstance(oc_tracer.tracer, NoopTracer)
        self.assertNotIsInstance(oc_tracer.tracer, ShimTracer)

        install_shim()

        # The property should cause existing instances to get the singleton ShimTracer
        self.assertIsInstance(oc_tracer.tracer, ShimTracer)

    def test_install_shim_affects_new_tracers(self):
        install_shim()

        # The property should cause existing instances to get the singleton ShimTracer
        oc_tracer = Tracer()
        self.assertIsInstance(oc_tracer.tracer, ShimTracer)

    def test_uninstall_shim_resets_tracer(self):
        install_shim()
        uninstall_shim()

        # The actual Tracer class should not be patched
        self.assertFalse(hasattr(Tracer, "tracer"))

    def test_uninstall_shim_resets_existing_tracers(self):
        oc_tracer = Tracer()
        orig = oc_tracer.tracer
        install_shim()
        uninstall_shim()

        # Accessing the tracer member should no longer use the property, and instead should get
        # its original NoopTracer
        self.assertIs(oc_tracer.tracer, orig)

    def test_uninstall_shim_resets_new_tracers(self):
        install_shim()
        uninstall_shim()

        # Accessing the tracer member should get the NoopTracer
        oc_tracer = Tracer()
        self.assertIsInstance(oc_tracer.tracer, NoopTracer)
        self.assertNotIsInstance(oc_tracer.tracer, ShimTracer)
