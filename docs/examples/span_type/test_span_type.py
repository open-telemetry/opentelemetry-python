# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Checks the span the span_type.py example emits against
``weaver registry live-check``.

The registry in ``registry/`` is a semantic conventions schema v2 registry
defining a single span, ``gen_ai.client.inference``, with one required and one
recommended attribute -- the same type the example passes to
``start_as_current_span(span_type=...)``.

Requires the ``weaver`` binary on PATH:
  https://github.com/open-telemetry/weaver/releases
"""

import os
import shutil
import unittest

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.test.weaver_live_check import (
    LiveCheckError,
    WeaverLiveCheck,
)
from opentelemetry.trace import SpanKind

_DIR = os.path.dirname(os.path.abspath(__file__))
_REGISTRY_DIR = os.path.join(_DIR, "registry")

SPAN_TYPE = "gen_ai.client.inference"

# gen_ai.operation.name is required by the span definition,
# gen_ai.request.model is only recommended.
CONFORMANT_ATTRIBUTES = {"gen_ai.operation.name": "chat"}


def _emit_and_collect(attributes: dict) -> dict:
    """Emit the example's span into live-check, return the span sample."""
    with WeaverLiveCheck(
        registry=_REGISTRY_DIR,
        # --v2 is required for the registry to load as schema v2; without it
        # weaver downconverts to v1, where spans have no type.
        extra_args=["--v2", "--config", os.path.join(_DIR, "weaver.toml")],
    ) as weaver:
        provider = TracerProvider()
        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(endpoint=weaver.otlp_endpoint, insecure=True)
            )
        )
        with provider.get_tracer(__name__).start_as_current_span(
            "chat gpt-4o-mini",
            kind=SpanKind.CLIENT,
            span_type=SPAN_TYPE,
            attributes=attributes,
        ):
            pass
        provider.force_flush()
        # validates the span against the registry and returns the report
        # with details
        # it'll fail if anny violations are found
        report = weaver.end_and_check()

    spans = [s["span"] for s in report.get("samples", []) if "span" in s]
    assert len(spans) == 1, f"expected one span, got {len(spans)}"
    return {"span": spans[0], "report": report}


@unittest.skipUnless(
    shutil.which("weaver") is not None,
    "weaver binary not found on PATH — install from https://github.com/open-telemetry/weaver/releases",
)
class TestSpanTypeExample(unittest.TestCase):
    def test_span_type_reaches_weaver(self):
        """The span type set at creation arrives at live-check.

        Until OTLP has a top-level ``Span.type`` field the exporter carries it
        as the ``otel.span.type`` attribute, so that is what weaver sees.
        """
        result = _emit_and_collect(CONFORMANT_ATTRIBUTES)
        attributes = {
            a["name"]: a["value"] for a in result["span"]["attributes"]
        }
        self.assertEqual(attributes.get("otel.span.type"), SPAN_TYPE)

    def test_live_check_resolves_span_by_type(self):
        """What span type is for: live-check resolves the span to its
        definition and checks it against that definition.

        The example omits ``gen_ai.request.model``, which the registry marks
        recommended, so live-check advises on it. Nothing about the span name or
        its attributes is used to find the definition -- only the type.
        """
        result = _emit_and_collect(CONFORMANT_ATTRIBUTES)
        advice = result["span"]["live_check_result"]["all_advice"]

        # improvement, not a violation, so end_and_check() above did not raise:
        #   Recommended attribute 'gen_ai.request.model' is not present.
        self.assertEqual(len(advice), 1, advice)
        self.assertEqual(advice[0]["id"], "recommended_attribute_not_present")
        self.assertEqual(
            advice[0]["context"]["attribute_key"], "gen_ai.request.model"
        )

    def test_missing_required_attribute_fails(self):
        """Dropping a required attribute fails the live check.

        Only possible because the span resolved to its definition -- without a
        span type weaver has nothing to compare the attributes against.
        """
        with self.assertRaises(LiveCheckError) as ctx:
            _emit_and_collect({})

        # Semconv violations found:
        # - [required_attribute_not_present] Required attribute
        #   'gen_ai.operation.name' is not present. (1 occurrence(s) on span
        #   'gen_ai.client.inference')
        violations = ctx.exception.report.violations
        self.assertEqual(len(violations), 1, violations)
        self.assertEqual(violations[0]["id"], "required_attribute_not_present")
        self.assertEqual(
            violations[0]["context"]["attribute_key"], "gen_ai.operation.name"
        )

    def test_unknown_attribute_fails(self):
        """An attribute the registry does not define fails the live check."""
        with self.assertRaises(LiveCheckError) as ctx:
            _emit_and_collect(
                {**CONFORMANT_ATTRIBUTES, "gen_ai.made.up": "value"}
            )

        # Semconv violations found:
        # - [missing_attribute] Attribute 'gen_ai.made.up' does not exist in
        #   the registry. (1 occurrence(s) on span 'gen_ai.client.inference')
        violations = ctx.exception.report.violations
        self.assertEqual(len(violations), 1, violations)
        self.assertEqual(violations[0]["id"], "missing_attribute")
        self.assertEqual(
            violations[0]["context"]["attribute_key"], "gen_ai.made.up"
        )
