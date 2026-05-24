# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry.test.test_base import TestBase


class TestBaseTestCase(TestBase):
    def test_get_sorted_metrics_works_without_metrics(self):
        metrics = self.get_sorted_metrics()
        self.assertEqual(metrics, [])
