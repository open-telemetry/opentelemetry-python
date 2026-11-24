# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import _logs as logs_api
from opentelemetry.test.test_base import TestBase


class TestBaseTestCase(TestBase):
    def test_get_sorted_metrics_works_without_metrics(self):
        metrics = self.get_sorted_metrics()
        self.assertEqual(metrics, [])

    def test_get_finished_logs(self):
        self.assertEqual(self.get_finished_logs(), ())
        logger = logs_api.get_logger("test-logger")
        logger.emit(body="hello world")
        finished_logs = self.get_finished_logs()
        self.assertEqual(len(finished_logs), 1)
        self.assertEqual(finished_logs[0].log_record.body, "hello world")
