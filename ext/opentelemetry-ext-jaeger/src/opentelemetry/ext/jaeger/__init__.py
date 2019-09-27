# Copyright 2018, OpenCensus Authors
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

"""Jaeger Span Exporter for OpenTelemetry."""

import logging
import socket
import typing

from thrift.protocol import TBinaryProtocol, TCompactProtocol
from thrift.transport import THttpClient, TTransport

import opentelemetry.trace as trace_api
from opentelemetry.ext.jaeger.gen.jaeger import agent, jaeger
from opentelemetry.sdk.trace.export import Span, SpanExporter, SpanExportResult

DEFAULT_AGENT_HOST_NAME = "localhost"
DEFAULT_AGENT_PORT = 6831
DEFAULT_COLLECTOR_ENDPOINT = "/api/traces?format=jaeger.thrift"

UDP_PACKET_MAX_LENGTH = 65000

logger = logging.getLogger(__name__)


class JaegerSpanExporter(SpanExporter):
    """Jaeger span exporter for OpenTelemetry.

    Args:
        service_name: Service that logged an annotation in a trace.Classifier
            when query for spans.
        collector_host_name: (Optional) The host name of the Jaeger-Collector
            HTTP Thrift.
        collector_port: (Optional) The port of the Jaeger-Collector HTTP
            Thrift.
        username: (Optional) The user name of the Basic Auth if authentication
            is required.
        password: (Optional) The password of the Basic Auth if authentication
            is required.
        collector_endpoint: (Optional) The endpoint of the Jaeger-Collector
            HTTP Thrift.
        agent_host_name: (Optional) The host name of the Jaeger-Agent.
        agent_port: (Optional) The port of the Jaeger-Agent.
    """

    def __init__(
        self,
        service_name: str = "my_service",
        agent_host_name: str = DEFAULT_AGENT_HOST_NAME,
        agent_port: int = DEFAULT_AGENT_PORT,
        collector_host_name: str = None,
        collector_port: int = None,
        collector_endpoint: str = DEFAULT_COLLECTOR_ENDPOINT,
        username: str = None,
        password: str = None,
    ):
        self.service_name = service_name
        self.agent_host_name = agent_host_name
        self.agent_port = agent_port
        self._agent_client = None
        self.collector_host_name = collector_host_name
        self.collector_port = collector_port
        self.collector_endpoint = collector_endpoint
        self.username = username
        self.password = password
        self._collector = None

    @property
    def agent_client(self):
        if self._agent_client is None:
            self._agent_client = AgentClientUDP(
                host_name=self.agent_host_name, port=self.agent_port
            )
        return self._agent_client

    @property
    def collector(self):
        if self._collector is not None:
            return self._collector

        if self.collector_host_name is None or self.collector_port is None:
            return None

        thrift_url = "http://{}:{}{}".format(
            self.collector_host_name,
            self.collector_port,
            self.collector_endpoint or DEFAULT_COLLECTOR_ENDPOINT,
        )

        auth = None
        if self.username is not None and self.password is not None:
            auth = (self.username, self.password)

        self._collector = Collector(thrift_url=thrift_url, auth=auth)
        return self._collector

    def export(self, spans: typing.Sequence[Span]):
        jaeger_spans = self.translate_to_jaeger(spans)

        batch = jaeger.Batch(
            spans=jaeger_spans,
            process=jaeger.Process(serviceName=self.service_name),
        )

        if self.collector is not None:
            self.collector.submit(batch)
        self.agent_client.emit(batch)

        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass

    def translate_to_jaeger(self, spans: typing.Sequence[Span]):
        """Translate the spans to Jaeger format.

        Args:
            spans: Tuple of spans to convert
        """

        jaeger_spans = []

        for span in spans:
            trace_id = span.get_context().trace_id
            span_id = span.get_context().span_id

            start_time_us = span.start_time / 1e3
            end_time_us = span.end_time / 1e3
            duration_us = end_time_us - start_time_us

            parent_id = 0
            if isinstance(span.parent, trace_api.Span):
                parent_id = span.parent.get_context().span_id
            elif isinstance(span.parent, trace_api.SpanContext):
                parent_id = span.parent.span_id

            tags = _extract_tags(span.attributes)

            # TODO: status is missing:
            # https://github.com/open-telemetry/opentelemetry-python/issues/98

            refs = _extract_refs_from_span(span)
            logs = _extract_logs_from_span(span)

            flags = int(span.get_context().trace_options)

            jaeger_span = jaeger.Span(
                traceIdHigh=_get_trace_id_high(trace_id),
                traceIdLow=_get_trace_id_low(trace_id),
                # generated code expects i64
                spanId=_convert_int_to_i64(span_id),
                operationName=span.name,
                startTime=int(start_time_us),
                duration=int(duration_us),
                tags=tags,
                logs=logs,
                references=refs,
                flags=flags,
                parentSpanId=_convert_int_to_i64(parent_id),
            )

            jaeger_spans.append(jaeger_span)

        return jaeger_spans


def _extract_refs_from_span(span):
    if not span.links:
        return None

    refs = []
    for link in span.links:
        trace_id = link.context.trace_id
        span_id = link.context.span_id
        refs.append(
            jaeger.SpanRef(
                refType=jaeger.SpanRefType.FOLLOWS_FROM,
                traceIdHigh=_get_trace_id_high(trace_id),
                traceIdLow=_get_trace_id_low(trace_id),
                spanId=_convert_int_to_i64(span_id),
            )
        )
    return refs


def _convert_int_to_i64(val):
    """Convert integer to signed int64 (i64)"""
    if val > 0x7FFFFFFFFFFFFFFF:
        val -= 0x10000000000000000
    return val


def _get_trace_id_low(trace_id):
    return _convert_int_to_i64(trace_id & 0xFFFFFFFFFFFFFFFF)


def _get_trace_id_high(trace_id):
    return _convert_int_to_i64((trace_id >> 64) & 0xFFFFFFFFFFFFFFFF)


def _extract_logs_from_span(span):
    if not span.events:
        return None

    logs = []

    for event in span.events:
        fields = []
        if event.attributes is not None:
            fields = _extract_tags(event.attributes)

        fields.append(
            jaeger.Tag(
                key="message", vType=jaeger.TagType.STRING, vStr=event.name
            )
        )

        event_timestamp_us = event.timestamp / 1e3
        logs.append(
            jaeger.Log(timestamp=int(event_timestamp_us), fields=fields)
        )
    return logs


def _extract_tags(attr):
    if not attr:
        return []
    tags = []
    for attribute_key, attribute_value in attr.items():
        tag = _convert_attribute_to_tag(attribute_key, attribute_value)
        if tag is None:
            continue
        tags.append(tag)
    return tags


def _convert_attribute_to_tag(key, attr):
    """Convert the attributes to jaeger tags."""
    if isinstance(attr, bool):
        return jaeger.Tag(key=key, vBool=attr, vType=jaeger.TagType.BOOL)
    if isinstance(attr, str):
        return jaeger.Tag(key=key, vStr=attr, vType=jaeger.TagType.STRING)
    if isinstance(attr, int):
        return jaeger.Tag(key=key, vLong=attr, vType=jaeger.TagType.LONG)
    if isinstance(attr, float):
        return jaeger.Tag(key=key, vDouble=attr, vType=jaeger.TagType.DOUBLE)
    logger.warning("Could not serialize attribute %s:%r to tag", key, attr)
    return None


class AgentClientUDP:
    """Implement a UDP client to agent.

    Args:
        host_name: The host name of the Jaeger server.
        port: The port of the Jaeger server.
        max_packet_size: (Optional) Maximum size of UDP packet.
        client: Class for creating new client objects for agencies. It should
            extend from the agent :class: `.AgentIface` type and implement
            :meth:`.AgentIface.emitBatch`. Default and only option to
            :class:`.AgentClient`.
    """

    def __init__(
        self,
        host_name: str,
        port: int,
        max_packet_size: int = UDP_PACKET_MAX_LENGTH,
        client=agent.Client,
    ):
        self.address = (host_name, port)
        self.max_packet_size = max_packet_size
        self.buffer = TTransport.TMemoryBuffer()
        self.client = client(
            iprot=TCompactProtocol.TCompactProtocol(trans=self.buffer)
        )

    def emit(self, batch: jaeger.Batch):
        """
        Args:
            batch: Object to emit Jaeger spans.
        """

        self.client._seqid = 0
        #  truncate and reset the position of BytesIO object
        self.buffer._buffer.truncate(0)
        self.buffer._buffer.seek(0)
        self.client.emitBatch(batch)
        buff = self.buffer.getvalue()
        if len(buff) > self.max_packet_size:
            logger.warning(
                "Data exceeds the max UDP packet size; size %r, max %r",
                len(buff),
                self.max_packet_size,
            )
            return

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.sendto(buff, self.address)


class Collector:
    """Submits collected spans to Thrift HTTP server.

    Args:
        thrift_url: URL of the Jaeger HTTP Thrift.
        auth: (Optional) Auth tuple that contains username and password for
            Basic Auth.
        http_transport: Class for creating new client for Thrift HTTP server.
    """

    def __init__(
        self,
        thrift_url: str = "",
        auth: typing.Tuple[str, str] = None,
        client=jaeger.Client,
        http_transport=THttpClient.THttpClient,
    ):
        self.thrift_url = thrift_url
        self.auth = auth
        self.http_transport = http_transport(uri_or_host=thrift_url)
        self.client = client(
            iprot=TBinaryProtocol.TBinaryProtocol(trans=self.http_transport)
        )

        # set basic auth header
        if auth is not None:
            import base64

            auth_header = "{}:{}".format(*auth)
            decoded = base64.b64encode(auth_header.encode()).decode("ascii")
            basic_auth = dict(Authorization="Basic {}".format(decoded))
            self.http_transport.setCustomHeaders(basic_auth)

    def submit(self, batch: jaeger.Batch):
        """Submits batches to Thrift HTTP Server through Binary Protocol.

        Args:
            batch: Object to emit Jaeger spans.
        """
        try:
            self.client.submitBatches([batch])
            # it will call http_transport.flush() and
            # status code and message will be updated
            code = self.http_transport.code
            msg = self.http_transport.message
            if code >= 300 or code < 200:
                logger.error(
                    "Traces cannot be uploaded;\
                        HTTP status code: {}, message {}".format(
                        code, msg
                    )
                )
        finally:
            if self.http_transport.isOpen():
                self.http_transport.close()
