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

"""Zipkin Exporter Sender for HTTP JSON and protobuf requests"""

import logging
import requests
from typing import List, Optional, Sequence

from opentelemetry.exporter.zipkin.encoder import Encoding
from opentelemetry.exporter.zipkin.sender import Sender
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.trace import Span

DEFAULT_ENCODING = Encoding.JSON_V2
SUCCESS_STATUS_CODES = (200, 202)

logger = logging.getLogger(__name__)


class HttpSender(Sender):
    def __init__(
        self, endpoint: str, encoding: Optional[Encoding] = DEFAULT_ENCODING,
    ):
        super().__init__(endpoint, encoding)

    def send(self, encoded_spans: Sequence[Span]) -> SpanExportResult:

        result = requests.post(
            url=self.endpoint,
            data=encoded_spans,
            headers={"Content-Type": self.content_type()},
        )

        if result.status_code not in SUCCESS_STATUS_CODES:
            logger.error(
                "Traces cannot be uploaded; status code: %s, message %s",
                result.status_code,
                result.text,
            )

            return SpanExportResult.FAILURE
        return SpanExportResult.SUCCESS

    @staticmethod
    def supported_encodings() -> List[Encoding]:
        return [Encoding.JSON_V1, Encoding.JSON_V2, Encoding.PROTOBUF]

    def content_type(self):
        if self.encoding == Encoding.PROTOBUF:
            content_type = "application/x-protobuf"
        else:
            content_type = "application/json"
        return content_type
