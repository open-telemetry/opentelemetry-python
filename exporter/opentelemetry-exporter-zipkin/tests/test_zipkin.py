# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest

from opentelemetry.exporter.zipkin import json
from opentelemetry.exporter.zipkin.proto import http


class TestZipkinExporter(unittest.TestCase):
    def test_constructors(self):
        try:
            json.ZipkinExporter()
            http.ZipkinExporter()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.assertIsNone(exc)
