# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
# type: ignore

from importlib.util import find_spec
from unittest import TestCase


class TestInstrumentor(TestCase):
    def test_proto(self):
        if find_spec("opentelemetry.proto_json") is None:
            self.fail("opentelemetry-proto-json not installed")
