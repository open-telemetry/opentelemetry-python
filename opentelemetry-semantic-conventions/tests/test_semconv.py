# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
# type: ignore

from importlib.util import find_spec
from unittest import TestCase


class TestSemanticConventions(TestCase):
    def test_semantic_conventions(self):
        if find_spec("opentelemetry.semconv") is None:
            self.fail("opentelemetry-semantic-conventions not installed")
