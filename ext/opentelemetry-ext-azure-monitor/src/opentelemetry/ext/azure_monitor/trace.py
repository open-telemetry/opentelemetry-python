# Copyright 2019, OpenTelemetry Authors
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

import json
import logging
from urllib.parse import urlparse

import requests

from opentelemetry.ext.azure_monitor import protocol, util
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.util import ns_to_iso_str
from opentelemetry.trace import Span, SpanKind

logger = logging.getLogger(__name__)


class AzureMonitorSpanExporter(SpanExporter):
    def __init__(self, **options):
        self.options = util.Options(**options)
        if not self.options.instrumentation_key:
            raise ValueError("The instrumentation_key is not provided.")

    def export(self, spans):
        envelopes = tuple(map(self.span_to_envelope, spans))

        try:
            response = requests.post(
                url=self.options.endpoint,
                data=json.dumps(envelopes),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json; charset=utf-8",
                },
                timeout=self.options.timeout,
            )
        except requests.RequestException as ex:
            logger.warning("Transient client side error %s.", ex)
            return SpanExportResult.FAILED_RETRYABLE

        text = "N/A"
        data = None  # noqa pylint: disable=unused-variable
        try:
            text = response.text
        except Exception as ex:  # noqa pylint: disable=broad-except
            logger.warning("Error while reading response body %s.", ex)
        else:
            try:
                data = json.loads(text)  # noqa pylint: disable=unused-variable
            except Exception:  # noqa pylint: disable=broad-except
                pass

        if response.status_code == 200:
            logger.info("Transmission succeeded: %s.", text)
            return SpanExportResult.SUCCESS

        if response.status_code in (
            206,  # Partial Content
            429,  # Too Many Requests
            500,  # Internal Server Error
            503,  # Service Unavailable
        ):
            return SpanExportResult.FAILED_RETRYABLE

        return SpanExportResult.FAILED_NOT_RETRYABLE

    @staticmethod
    def ns_to_duration(nanoseconds):
        value = (nanoseconds + 500000) // 1000000  # duration in milliseconds
        value, microseconds = divmod(value, 1000)
        value, seconds = divmod(value, 60)
        value, minutes = divmod(value, 60)
        days, hours = divmod(value, 24)
        return "{:d}.{:02d}:{:02d}:{:02d}.{:03d}".format(
            days, hours, minutes, seconds, microseconds
        )

    def span_to_envelope(self, span):
        envelope = protocol.Envelope(
            iKey=self.options.instrumentation_key,
            tags=dict(util.azure_monitor_context),
            time=ns_to_iso_str(span.start_time),
        )
        envelope.tags["ai.operation.id"] = "{:032x}".format(
            span.context.trace_id
        )
        if span.parent:
            parent = span.parent
            if isinstance(parent, Span):
                parent = parent.context
            envelope.tags[
                "ai.operation.parentId"
            ] = "|{:032x}.{:016x}.".format(
                parent.trace_id, parent.span_id
            )
        if span.kind in (SpanKind.CONSUMER, SpanKind.SERVER):
            envelope.name = "Microsoft.ApplicationInsights.Request"
            data = protocol.Request(
                id="|{:032x}.{:016x}.".format(
                    span.context.trace_id, span.context.span_id
                ),
                duration=self.ns_to_duration(span.end_time - span.start_time),
                responseCode="0",
                success=False,
                properties={},
            )
            envelope.data = protocol.Data(
                baseData=data, baseType="RequestData"
            )
            if "http.method" in span.attributes:
                data.name = span.attributes["http.method"]
            if "http.route" in span.attributes:
                data.name = data.name + " " + span.attributes["http.route"]
                envelope.tags["ai.operation.name"] = data.name
            if "http.url" in span.attributes:
                data.url = span.attributes["http.url"]
            if "http.status_code" in span.attributes:
                status_code = span.attributes["http.status_code"]
                data.responseCode = str(status_code)
                data.success = 200 <= status_code < 400
        else:
            envelope.name = "Microsoft.ApplicationInsights.RemoteDependency"
            data = protocol.RemoteDependency(
                name=span.name,
                id="|{:032x}.{:016x}.".format(
                    span.context.trace_id, span.context.span_id
                ),
                resultCode="0",  # TODO
                duration=self.ns_to_duration(span.end_time - span.start_time),
                success=True,  # TODO
                properties={},
            )
            envelope.data = protocol.Data(
                baseData=data, baseType="RemoteDependencyData"
            )
            if span.kind in (SpanKind.CLIENT, SpanKind.PRODUCER):
                data.type = "HTTP"  # TODO
                if "http.url" in span.attributes:
                    url = span.attributes["http.url"]
                    # TODO: error handling, probably put scheme as well
                    data.name = urlparse(url).netloc
                if "http.status_code" in span.attributes:
                    data.resultCode = str(span.attributes["http.status_code"])
            else:  # SpanKind.INTERNAL
                data.type = "InProc"
        # TODO: links, tracestate, tags
        for key in span.attributes:
            data.properties[key] = span.attributes[key]
        return envelope
