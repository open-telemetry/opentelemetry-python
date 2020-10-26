# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from http import HTTPStatus

from opentelemetry.instrumentation.utils import http_status_to_canonical_code
from opentelemetry.test.test_base import TestBase
from opentelemetry.trace.status import StatusCode


class TestUtils(TestBase):
    def test_http_status_to_canonical_code(self):
        for status_code, expected in (
            (HTTPStatus.OK, StatusCode.OK),
            (HTTPStatus.ACCEPTED, StatusCode.OK),
            (HTTPStatus.IM_USED, StatusCode.OK),
            (HTTPStatus.MULTIPLE_CHOICES, StatusCode.OK),
            (HTTPStatus.BAD_REQUEST, StatusCode.OK),
            (HTTPStatus.UNAUTHORIZED, StatusCode.OK),
            (HTTPStatus.FORBIDDEN, StatusCode.OK),
            (HTTPStatus.NOT_FOUND, StatusCode.OK),
            (
                HTTPStatus.UNPROCESSABLE_ENTITY,
                StatusCode.OK,
            ),
            (
                HTTPStatus.TOO_MANY_REQUESTS,
                StatusCode.OK,
            ),
            (HTTPStatus.NOT_IMPLEMENTED, StatusCode.OK),
            (HTTPStatus.SERVICE_UNAVAILABLE, StatusCode.OK),
            (
                HTTPStatus.GATEWAY_TIMEOUT,
                StatusCode.OK,
            ),
            (
                HTTPStatus.HTTP_VERSION_NOT_SUPPORTED,
                StatusCode.OK,
            ),
            (600, StatusCode.OK),
            (99, StatusCode.OK),
        ):
            with self.subTest(status_code=status_code):
                actual = http_status_to_canonical_code(int(status_code))
                self.assertEqual(actual, expected, status_code)
