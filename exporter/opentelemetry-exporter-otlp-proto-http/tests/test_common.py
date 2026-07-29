# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest

import requests

from opentelemetry.exporter.otlp.proto.http._common import _is_retryable


class TestIsRetryable(unittest.TestCase):
    @staticmethod
    def _response(status_code: int) -> requests.Response:
        resp = requests.Response()
        resp.status_code = status_code
        return resp

    def test_retryable_status_codes(self):
        # 408 (Request Timeout), 429 (Too Many Requests) and any 5xx are
        # retryable per the OTLP specification.
        for status_code in (408, 429, 500, 502, 503, 504, 599):
            with self.subTest(status_code=status_code):
                self.assertTrue(_is_retryable(self._response(status_code)))

    def test_non_retryable_status_codes(self):
        for status_code in (200, 400, 401, 403, 404, 409):
            with self.subTest(status_code=status_code):
                self.assertFalse(_is_retryable(self._response(status_code)))
