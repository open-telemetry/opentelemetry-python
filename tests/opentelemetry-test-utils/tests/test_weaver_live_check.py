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

"""Live-check tests using Weaver to validate SDK telemetry against semconv.

Requires the `weaver` binary on PATH:
  https://github.com/open-telemetry/weaver/releases
"""

import os
import shutil
import unittest

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.test.weaver_live_check import WeaverLiveCheck

_TESTDATA_DIR = os.path.join(os.path.dirname(__file__), "testdata")


def _make_provider(otlp_endpoint: str) -> TracerProvider:
    resource = Resource.create({SERVICE_NAME: "test-service"})
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    return provider


@unittest.skipUnless(
    shutil.which("weaver") is not None,
    "weaver binary not found on PATH — install from https://github.com/open-telemetry/weaver/releases",
)
class TestSDKInitLiveCheck(unittest.TestCase):
    def test_sdk_resource_with_service_name(self):
        """SDK initialized with service.name emits conformant telemetry."""
        with WeaverLiveCheck() as weaver:
            provider = _make_provider(weaver.otlp_endpoint)
            with provider.get_tracer("test-tracer").start_as_current_span(
                "test-span"
            ):
                pass
            provider.force_flush()
            weaver.end_and_check()

    def test_custom_policy_violation_raises(self):
        """A policy that fails on never.use.this.attribute."""
        with WeaverLiveCheck(policies_dir=_TESTDATA_DIR) as weaver:
            provider = _make_provider(weaver.otlp_endpoint)
            with provider.get_tracer("test-tracer").start_as_current_span(
                "test-span"
            ) as span:
                span.set_attribute("never.use.this.attribute", "bad value")

            provider.force_flush()

            with self.assertRaises(AssertionError) as cm:
                weaver.end_and_check()

        self.assertIn("never.use.this.attribute", str(cm.exception))
