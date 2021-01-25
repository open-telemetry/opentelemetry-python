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

import abc

from opentelemetry.trace import SpanKind

OTLP_JAEGER_SPAN_KIND = {
    SpanKind.CLIENT: "client",
    SpanKind.SERVER: "server",
    SpanKind.CONSUMER: "consumer",
    SpanKind.PRODUCER: "producer",
    SpanKind.INTERNAL: "internal",
}

NAME_KEY = "otel.library.name"
VERSION_KEY = "otel.library.version"


def _nsec_to_usec_round(nsec: int) -> int:
    """Round nanoseconds to microseconds"""
    return (nsec + 500) // 10 ** 3


def _convert_int_to_i64(val):
    """Convert integer to signed int64 (i64)"""
    if val > 0x7FFFFFFFFFFFFFFF:
        val -= 0x10000000000000000
    return val


class Translator(abc.ABC):
    @abc.abstractmethod
    def _translate_span(self, span):
        """Translates span to jaeger format.

        Args:
            span: span to translate
        """

    @abc.abstractmethod
    def _extract_tags(self, span):
        """Extracts tags from span and returns list of jaeger Tags.

        Args:
            span: span to extract tags
        """

    @abc.abstractmethod
    def _extract_refs(self, span):
        """Extracts references from span and returns list of jaeger SpanRefs.

        Args:
            span: span to extract references
        """

    @abc.abstractmethod
    def _extract_logs(self, span):
        """Extracts logs from span and returns list of jaeger Logs.

        Args:
            span: span to extract logs
        """


class Translate:
    def __init__(self, spans):
        self.spans = spans

    def _translate(self, translator: Translator):
        translated_spans = []
        for span in self.spans:
            # pylint: disable=protected-access
            translated_span = translator._translate_span(span)
            translated_spans.append(translated_span)
        return translated_spans
