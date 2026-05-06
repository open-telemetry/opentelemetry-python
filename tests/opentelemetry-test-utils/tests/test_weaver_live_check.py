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

from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.test.weaver_live_check import (
    LiveCheckError,
    LiveCheckReport,
    WeaverLiveCheck,
)

try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # pylint: disable=no-name-in-module
        OTLPSpanExporter,
    )

    _HAS_GRPC = True
except ImportError:
    _HAS_GRPC = False

_TESTDATA_DIR = os.path.join(os.path.dirname(__file__), "testdata")
_REGISTRY_DIR = os.path.join(_TESTDATA_DIR, "registry")


def _make_provider(otlp_endpoint: str) -> TracerProvider:
    resource = Resource.create({SERVICE_NAME: "test-service"})
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    return provider


@unittest.skipUnless(
    _HAS_GRPC,
    "grpc exporter not installed",
)
@unittest.skipUnless(
    shutil.which("weaver") is not None,
    "weaver binary not found on PATH — install from https://github.com/open-telemetry/weaver/releases",
)
class TestSDKInitLiveCheck(unittest.TestCase):
    def test_end_and_check_no_violations(self):
        """end_and_check() returns a LiveCheckReport with no violations on conformant telemetry."""
        with WeaverLiveCheck(registry=_REGISTRY_DIR) as weaver:
            provider = _make_provider(weaver.otlp_endpoint)
            with provider.get_tracer("test-tracer").start_as_current_span(
                "test-span"
            ):
                pass
            provider.force_flush()
            report = weaver.end_and_check()

        self.assertIsInstance(report, LiveCheckReport)
        self.assertEqual(report.violations, [])

    def test_end_and_check_raises_on_violations(self):
        """end_and_check() raises LiveCheckError with the report attached."""
        with WeaverLiveCheck(
            registry=_REGISTRY_DIR, policies_dir=_TESTDATA_DIR
        ) as weaver:
            provider = _make_provider(weaver.otlp_endpoint)
            with provider.get_tracer("test-tracer").start_as_current_span(
                "test-span"
            ) as span:
                span.set_attribute("never.use.this.attribute", "bad value")

            provider.force_flush()

            with self.assertRaises(LiveCheckError) as cm:
                weaver.end_and_check()

        # Human-readable message lists the violation
        self.assertIn(
            "never.use.this.attribute is forbidden by this bogus policy",
            str(cm.exception),
        )
        # Structured report is attached for programmatic inspection
        self.assertTrue(
            any(
                v["id"] == "test_check"
                and v["context"].get("attribute_name")
                == "never.use.this.attribute"
                for v in cm.exception.report.violations
            )
        )

    def test_end_no_violations(self):
        """end() returns a LiveCheckReport with no violations on conformant telemetry."""
        with WeaverLiveCheck(registry=_REGISTRY_DIR) as weaver:
            provider = _make_provider(weaver.otlp_endpoint)
            with provider.get_tracer("test-tracer").start_as_current_span(
                "test-span"
            ):
                pass
            provider.force_flush()
            report = weaver.end()

        self.assertIsInstance(report, LiveCheckReport)
        self.assertEqual(report.violations, [])
        # LiveCheckReport supports dict-style access to the raw report data
        self.assertIn("statistics", report)
        self.assertIsNotNone(report.get("statistics"))
        self.assertIsNone(report.get("nonexistent"))

    def test_end_with_violations(self):
        """end() returns a LiveCheckReport with violations without raising."""
        with WeaverLiveCheck(
            registry=_REGISTRY_DIR, policies_dir=_TESTDATA_DIR
        ) as weaver:
            provider = _make_provider(weaver.otlp_endpoint)
            with provider.get_tracer("test-tracer").start_as_current_span(
                "test-span"
            ) as span:
                span.set_attribute("never.use.this.attribute", "bad value")

            provider.force_flush()
            report = weaver.end()

        self.assertIsInstance(report, LiveCheckReport)
        # Check the violation id (maps to advice_type in the rego policy)
        self.assertTrue(
            any(v["id"] == "test_check" for v in report.violations)
        )
        # Check the structured context identifies the offending attribute by name
        self.assertTrue(
            any(
                isinstance(v["context"], dict)
                and v["context"].get("attribute_name")
                == "never.use.this.attribute"
                for v in report.violations
            )
        )

    def test_report_span_statistics(self):
        """The full report exposes span counts and individual span samples."""
        with WeaverLiveCheck(registry=_REGISTRY_DIR) as weaver:
            provider = _make_provider(weaver.otlp_endpoint)
            with provider.get_tracer("test-tracer").start_as_current_span(
                "test-span"
            ):
                pass
            provider.force_flush()
            report = weaver.end()

        # Individual spans are accessible in report["samples"], each entry
        # with a "span" key containing the span data.
        span_samples = [
            s["span"] for s in report.get("samples", []) if "span" in s
        ]
        self.assertTrue(
            any(s["name"] == "test-span" for s in span_samples),
            f"Expected 'test-span' in samples, got: {[s['name'] for s in span_samples]}",
        )
