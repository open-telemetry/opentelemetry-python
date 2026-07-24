# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

from requests.models import Response

from opentelemetry.exporter.otlp.proto.http._common import (
    _extract_retry_after,
    _is_retryable,
)


def _response(status_code: int, retry_after: str | None = None) -> Response:
    resp = Response()
    resp.status_code = status_code
    if retry_after is not None:
        resp.headers["Retry-After"] = retry_after
    return resp


class TestIsRetryable(unittest.TestCase):
    def test_retryable_status_codes(self):
        # The OTLP specification lists exactly these codes as retryable.
        for status_code in (429, 502, 503, 504):
            with self.subTest(status_code=status_code):
                self.assertTrue(_is_retryable(_response(status_code)))

    def test_non_retryable_status_codes(self):
        # The specification requires that every other 4xx and 5xx code is not
        # retried, including 408 and 5xx codes outside the table above.
        for status_code in (200, 400, 401, 404, 408, 500, 501, 505):
            with self.subTest(status_code=status_code):
                self.assertFalse(_is_retryable(_response(status_code)))


class TestExtractRetryAfter(unittest.TestCase):
    def test_missing_header(self):
        self.assertIsNone(_extract_retry_after(_response(429)))

    def test_delay_seconds(self):
        self.assertEqual(_extract_retry_after(_response(429, "30")), 30.0)

    def test_delay_seconds_surrounding_whitespace(self):
        self.assertEqual(_extract_retry_after(_response(429, " 30 ")), 30.0)

    def test_header_name_is_case_insensitive(self):
        resp = Response()
        resp.status_code = 429
        resp.headers["retry-after"] = "7"
        self.assertEqual(_extract_retry_after(resp), 7.0)

    def test_zero_delay_is_honoured_as_immediate_retry(self):
        # A server asking for a zero-second delay gets a retry with no backoff.
        # This matches the specification's "honour the value" requirement, so
        # the caller must not treat 0.0 as "no header present".
        self.assertEqual(_extract_retry_after(_response(429, "0")), 0.0)

    def test_negative_delay_clamped_to_zero(self):
        self.assertEqual(_extract_retry_after(_response(429, "-5")), 0.0)

    def test_non_finite_delay_falls_back_to_backoff(self):
        for value in ("inf", "-inf", "nan"):
            with self.subTest(value=value):
                self.assertIsNone(_extract_retry_after(_response(429, value)))

    def test_malformed_header_falls_back_to_backoff(self):
        for value in ("", "soon", "Wed, 99 Xxx 2015 07:28:00 GMT"):
            with self.subTest(value=value):
                self.assertIsNone(_extract_retry_after(_response(429, value)))

    def test_http_date_in_the_future(self):
        retry_at = datetime.now(timezone.utc) + timedelta(seconds=30)
        retry_after = _extract_retry_after(
            _response(429, format_datetime(retry_at, usegmt=True))
        )
        # Second-granularity truncation in the HTTP-date format costs up to 1s.
        self.assertAlmostEqual(retry_after, 30.0, delta=1.5)

    def test_http_date_in_the_past_is_immediate_retry(self):
        retry_at = datetime.now(timezone.utc) - timedelta(seconds=30)
        self.assertEqual(
            _extract_retry_after(
                _response(429, format_datetime(retry_at, usegmt=True))
            ),
            0.0,
        )

    def test_naive_http_date_is_treated_as_utc(self):
        # A "-0000" offset means "unknown local offset" and parses to a naive
        # datetime, which is interpreted as UTC rather than local time.
        retry_at = datetime.now(timezone.utc) + timedelta(seconds=30)
        header = retry_at.strftime("%a, %d %b %Y %H:%M:%S -0000")
        retry_after = _extract_retry_after(_response(429, header))
        self.assertAlmostEqual(retry_after, 30.0, delta=1.5)
