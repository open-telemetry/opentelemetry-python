# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import unittest
from logging import WARNING, getLogger
from unittest.mock import Mock

from opentelemetry.exporter.otlp.common._partial_success import (
    _report_partial_success,
)

_logger = getLogger(__name__)
_ENDPOINT = "http://collector.test/v1/traces"


class TestReportPartialSuccess(unittest.TestCase):
    def test_nothing_rejected_and_no_message_is_not_reported(self):
        with self.assertNoLogs(_logger, WARNING):
            self.assertEqual(_report_partial_success(_logger, "spans", _ENDPOINT, 0, ""), 0)

    def test_rejected_items_are_reported_with_the_error_message(self):
        with self.assertLogs(_logger, WARNING) as logs:
            rejected = _report_partial_success(_logger, "spans", _ENDPOINT, 2, "quota exceeded")

        self.assertEqual(rejected, 2)
        self.assertEqual(
            logs.records[0].getMessage(),
            "OTLP partial success exporting spans to http://collector.test/v1/traces (rejected=2): quota exceeded",
        )

    def test_rejected_items_are_reported_without_an_error_message(self):
        with self.assertLogs(_logger, WARNING) as logs:
            rejected = _report_partial_success(_logger, "metrics", _ENDPOINT, 7, "")

        self.assertEqual(rejected, 7)
        self.assertEqual(
            logs.records[0].getMessage(),
            "OTLP partial success exporting metrics to http://collector.test/v1/traces (rejected=7): ",
        )

    def test_an_error_message_alone_is_reported(self):
        with self.assertLogs(_logger, WARNING) as logs:
            rejected = _report_partial_success(_logger, "logs", _ENDPOINT, 0, "deprecated attribute in use")

        self.assertEqual(rejected, 0)
        self.assertEqual(
            logs.records[0].getMessage(),
            "OTLP partial success exporting logs to http://collector.test/v1/traces (rejected=0): "
            "deprecated attribute in use",
        )

    def test_a_negative_rejected_count_is_reported_as_zero(self):
        with self.assertNoLogs(_logger, WARNING):
            self.assertEqual(_report_partial_success(_logger, "spans", _ENDPOINT, -1, ""), 0)

    def test_a_negative_rejected_count_beside_an_error_message_is_reported_as_zero(self):
        with self.assertLogs(_logger, WARNING) as logs:
            rejected = _report_partial_success(_logger, "spans", _ENDPOINT, -1, "quota exceeded")

        self.assertEqual(rejected, 0)
        self.assertEqual(
            logs.records[0].getMessage(),
            "OTLP partial success exporting spans to http://collector.test/v1/traces (rejected=0): quota exceeded",
        )

    def test_the_signal_is_an_argument_so_one_signal_does_not_mask_another(self):
        messages = set()
        for signal in ("spans", "metrics", "logs"):
            with self.assertLogs(_logger, WARNING) as logs:
                _report_partial_success(_logger, signal, _ENDPOINT, 1, "")
            messages.add(logs.records[0].msg)

        self.assertEqual(len(messages), 1)

    def test_the_arguments_stay_unformatted_until_the_record_is_rendered(self):
        with self.assertLogs(_logger, WARNING) as logs:
            _report_partial_success(_logger, "spans", _ENDPOINT, 2, "quota exceeded")

        self.assertEqual(logs.records[0].args, ("spans", _ENDPOINT, 2, "quota exceeded"))

    def test_a_logger_that_raises_does_not_propagate(self):
        logger = Mock()
        logger.warning.side_effect = RuntimeError("logging is broken")

        self.assertEqual(_report_partial_success(logger, "spans", _ENDPOINT, 2, "quota exceeded"), 0)
