# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest
from logging import DEBUG, WARNING, getLogger
from unittest.mock import patch

from opentelemetry.exporter.otlp.proto.common._internal._partial_success import (
    _REJECTED_FIELDS,
    _log_partial_success,
    _partial_success_detail,
    _warning_format,
)
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceResponse,
)
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceResponse,
)
from opentelemetry.proto.collector.profiles.v1development.profiles_service_pb2 import (
    ExportProfilesServiceResponse,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
    ExportTraceServiceResponse,
)

_logger = getLogger(__name__)
_ENDPOINT = "http://collector.test/v1/traces"


class TestPartialSuccessWarning(unittest.TestCase):
    def test_absent_partial_success_is_not_reported(self):
        self.assertIsNone(_partial_success_detail(ExportTraceServiceResponse()))

    def test_absent_response_is_not_reported(self):
        self.assertIsNone(_partial_success_detail(None))

    def test_a_message_type_without_the_field_is_not_reported(self):
        self.assertIsNone(_partial_success_detail(ExportTraceServiceRequest()))

    def test_zeroed_partial_success_is_not_reported(self):
        response = ExportTraceServiceResponse()
        response.partial_success.rejected_spans = 0
        response.partial_success.error_message = ""

        self.assertIsNone(_partial_success_detail(response))

    def test_rejected_spans_are_reported_with_the_error_message(self):
        response = ExportTraceServiceResponse()
        response.partial_success.rejected_spans = 3
        response.partial_success.error_message = "some spans were invalid"

        self.assertEqual(
            _partial_success_detail(response),
            "the server rejected 3 spans: some spans were invalid",
        )

    def test_rejected_spans_are_reported_without_an_error_message(self):
        response = ExportTraceServiceResponse()
        response.partial_success.rejected_spans = 5

        self.assertEqual(
            _partial_success_detail(response),
            "the server rejected 5 spans",
        )

    def test_error_message_alone_is_reported(self):
        response = ExportTraceServiceResponse()
        response.partial_success.error_message = "deprecated attribute in use"

        self.assertEqual(
            _partial_success_detail(response),
            "deprecated attribute in use",
        )

    def test_rejected_data_points_are_reported(self):
        response = ExportMetricsServiceResponse()
        response.partial_success.rejected_data_points = 7

        self.assertEqual(
            _partial_success_detail(response),
            "the server rejected 7 data points",
        )

    def test_rejected_log_records_are_reported(self):
        response = ExportLogsServiceResponse()
        response.partial_success.rejected_log_records = 2

        self.assertEqual(
            _partial_success_detail(response),
            "the server rejected 2 log records",
        )

    def test_rejected_profiles_are_reported(self):
        response = ExportProfilesServiceResponse()
        response.partial_success.rejected_profiles = 6

        self.assertEqual(
            _partial_success_detail(response),
            "the server rejected 6 profiles",
        )

    def test_a_single_rejected_item_is_reported_in_the_singular(self):
        responses = (
            (ExportTraceServiceResponse(), "rejected_spans", "span"),
            (ExportMetricsServiceResponse(), "rejected_data_points", "data point"),
            (ExportLogsServiceResponse(), "rejected_log_records", "log record"),
            (ExportProfilesServiceResponse(), "rejected_profiles", "profile"),
        )

        for response, field_name, kind in responses:
            with self.subTest(kind=kind):
                setattr(response.partial_success, field_name, 1)

                self.assertEqual(
                    _partial_success_detail(response),
                    f"the server rejected 1 {kind}",
                )

    def test_every_rejected_field_the_protos_define_is_covered(self):
        responses = (
            ExportTraceServiceResponse(),
            ExportMetricsServiceResponse(),
            ExportLogsServiceResponse(),
            ExportProfilesServiceResponse(),
        )

        for response in responses:
            with self.subTest(response=type(response).__name__):
                names = {field.name for field in response.partial_success.DESCRIPTOR.fields}
                rejected = {name for name in names if name.startswith("rejected_")}
                self.assertTrue(rejected.issubset(set(_REJECTED_FIELDS)))


class TestLogPartialSuccess(unittest.TestCase):
    def test_empty_body_logs_nothing(self):
        with self.assertNoLogs(_logger, WARNING):
            _log_partial_success(b"", ExportTraceServiceResponse, _logger, "spans", _ENDPOINT)

    def test_body_carrying_a_zeroed_partial_success_logs_nothing(self):
        zeroed = ExportTraceServiceResponse()
        zeroed.partial_success.rejected_spans = 0
        serialized = zeroed.SerializeToString()
        self.assertTrue(serialized)

        with self.assertNoLogs(_logger, WARNING):
            _log_partial_success(serialized, ExportTraceServiceResponse, _logger, "spans", _ENDPOINT)

    def test_body_with_partial_success_is_logged(self):
        response = ExportTraceServiceResponse()
        response.partial_success.rejected_spans = 4
        response.partial_success.error_message = "quota exceeded"

        with self.assertLogs(_logger, WARNING) as logs:
            _log_partial_success(response.SerializeToString(), ExportTraceServiceResponse, _logger, "spans", _ENDPOINT)

        self.assertEqual(
            logs.records[0].getMessage(),
            "OTLP partial success exporting spans to http://collector.test/v1/traces: "
            "the server rejected 4 spans: quota exceeded",
        )

    def test_the_logged_message_stays_constant_so_duplicates_collapse(self):
        records = []
        for rejected in (1, 2, 3):
            response = ExportTraceServiceResponse()
            response.partial_success.rejected_spans = rejected

            with self.assertLogs(_logger, WARNING) as logs:
                _log_partial_success(
                    response.SerializeToString(), ExportTraceServiceResponse, _logger, "spans", _ENDPOINT
                )
            records.append(logs.records[0])

        self.assertEqual({record.msg for record in records}, {_warning_format("spans")})
        self.assertEqual(len({record.getMessage() for record in records}), 3)

    def test_the_logged_message_differs_between_signals_so_they_do_not_collapse(self):
        records = []
        for signal in ("spans", "metrics", "logs"):
            response = ExportTraceServiceResponse()
            response.partial_success.rejected_spans = 1

            with self.assertLogs(_logger, WARNING) as logs:
                _log_partial_success(
                    response.SerializeToString(), ExportTraceServiceResponse, _logger, signal, _ENDPOINT
                )
            records.append(logs.records[0])

        self.assertEqual(len({record.msg for record in records}), 3)

    def test_unparsable_body_is_logged_at_debug_and_ignored(self):
        with self.assertLogs(_logger, DEBUG) as logs:
            _log_partial_success(b"\xff\xff\xff\xff", ExportTraceServiceResponse, _logger, "spans", _ENDPOINT)

        self.assertEqual([record.levelno for record in logs.records], [DEBUG])
        self.assertIn("Failed to parse the OTLP export response", logs.records[0].getMessage())

    def test_non_protobuf_body_is_not_warned_about(self):
        for body in (b"<html>ok</html>", b'{"partialSuccess":{}}'):
            with self.subTest(body=body), self.assertNoLogs(_logger, WARNING):
                _log_partial_success(body, ExportTraceServiceResponse, _logger, "spans", _ENDPOINT)

    def test_invalid_utf8_in_the_error_message_is_ignored(self):
        body = b"\x0a\x04\x12\x02\xff\xfe"

        with self.assertLogs(_logger, DEBUG) as logs:
            _log_partial_success(body, ExportTraceServiceResponse, _logger, "spans", _ENDPOINT)

        self.assertEqual([record.levelno for record in logs.records], [DEBUG])

    def test_a_parser_raising_unicode_decode_error_is_ignored(self):
        error = UnicodeDecodeError("utf-8", b"\xff\xfe", 0, 1, "invalid start byte")

        with patch.object(ExportTraceServiceResponse, "ParseFromString", side_effect=error):
            with self.assertLogs(_logger, DEBUG) as logs:
                _log_partial_success(b"irrelevant", ExportTraceServiceResponse, _logger, "spans", _ENDPOINT)

        self.assertEqual([record.levelno for record in logs.records], [DEBUG])
        self.assertIn("Failed to parse the OTLP export response", logs.records[0].getMessage())


if __name__ == "__main__":
    unittest.main()
