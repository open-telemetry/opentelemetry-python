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

"""Zipkin Exporter Sender interface"""

import abc
import logging
from typing import Sequence, Tuple

from opentelemetry.exporter.zipkin.encoder import Encoding
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.trace import Span

logger = logging.getLogger(__name__)


class Sender:
    """
    Sends a list of encoded spans to a transport such as http. Usually this
    involves encoding them into a message and enqueueing them for transport.
    The typical end recipient is a zipkin collector.

    The parameter is a list of encoded spans as opposed to an encoded message.
    This allows implementations flexibility on how to encode spans into a
    message. For example, a large span might need to be sent as a separate
    message to avoid transport limits. Also, logging transports like scribe
    will likely write each span as a separate log line.
    """

    def __init__(self, endpoint: str, encoding: Encoding):
        self.endpoint = endpoint

        if encoding not in self.supported_encodings():
            raise ValueError(
                "Encoding type %s is not supported by this sender", encoding
            )

        self.encoding = encoding

    @abc.abstractmethod
    def send(self, encoded_spans: Sequence[Span]) -> SpanExportResult:
        pass

    @staticmethod
    @abc.abstractmethod
    def supported_encodings() -> Tuple[Encoding, ...]:
        pass
