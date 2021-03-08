# Copyright 2018, OpenCensus Authors
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

"""
The **OpenTelemetry Jaeger Exporter** allows to export `OpenTelemetry`_ traces to `Jaeger`_.
This exporter always sends traces to the configured agent using the Thrift compact protocol over UDP.
When it is not feasible to deploy Jaeger Agent next to the application, for example, when the
application code is running as Lambda function, a collector can be configured to send spans
using either Thrift over HTTP or Protobuf via gRPC. If both agent and collector are configured,
the exporter sends traces only to the collector to eliminate the duplicate entries.

Usage
-----

.. code:: python

    from opentelemetry import trace
    from opentelemetry.exporter import jaeger
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    # create a JaegerExporter
    jaeger_exporter = jaeger.JaegerExporter(
        service_name='my-helloworld-service',
        # configure agent
        agent_host_name='localhost',
        agent_port=6831,
        # optional: configure also collector
        # collector_endpoint='http://localhost:14268/api/traces?format=jaeger.thrift',
        # username=xxxx, # optional
        # password=xxxx, # optional
        # insecure=True, # optional
        # credentials=xxx # optional channel creds
        # transport_format='protobuf' # optional
        # max_tag_value_length=None # optional
    )

    # Create a BatchSpanProcessor and add the exporter to it
    span_processor = BatchSpanProcessor(jaeger_exporter)

    # add to the tracer
    trace.get_tracer_provider().add_span_processor(span_processor)

    with tracer.start_as_current_span('foo'):
        print('Hello world!')

API
---
.. _Jaeger: https://www.jaegertracing.io/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
"""
# pylint: disable=protected-access

import logging
from os import environ
from typing import Optional

from grpc import ChannelCredentials, insecure_channel, secure_channel

from opentelemetry.exporter.jaeger import util
from opentelemetry.exporter.jaeger.gen import model_pb2
from opentelemetry.exporter.jaeger.gen.collector_pb2 import PostSpansRequest
from opentelemetry.exporter.jaeger.gen.collector_pb2_grpc import (
    CollectorServiceStub,
)
from opentelemetry.exporter.jaeger.gen.jaeger import Collector as jaeger_thrift
from opentelemetry.exporter.jaeger.send.thrift import AgentClientUDP, Collector
from opentelemetry.exporter.jaeger.translate import Translate
from opentelemetry.exporter.jaeger.translate.protobuf import ProtobufTranslator
from opentelemetry.exporter.jaeger.translate.thrift import ThriftTranslator
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_JAEGER_AGENT_HOST,
    OTEL_EXPORTER_JAEGER_AGENT_PORT,
    OTEL_EXPORTER_JAEGER_AGENT_SPLIT_OVERSIZED_BATCHES,
    OTEL_EXPORTER_JAEGER_ENDPOINT,
    OTEL_EXPORTER_JAEGER_PASSWORD,
    OTEL_EXPORTER_JAEGER_USER,
)
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

DEFAULT_AGENT_HOST_NAME = "localhost"
DEFAULT_AGENT_PORT = 6831
DEFAULT_GRPC_COLLECTOR_ENDPOINT = "localhost:14250"

UDP_PACKET_MAX_LENGTH = 65000

TRANSPORT_FORMAT_THRIFT = "thrift"
TRANSPORT_FORMAT_PROTOBUF = "protobuf"

logger = logging.getLogger(__name__)


class JaegerExporter(SpanExporter):
    """Jaeger span exporter for OpenTelemetry.

    Args:
        service_name: Service that logged an annotation in a trace.Classifier
            when query for spans.
        agent_host_name: The host name of the Jaeger-Agent.
        agent_port: The port of the Jaeger-Agent.
        collector_endpoint: The endpoint of the Jaeger collector that uses
            Thrift over HTTP/HTTPS or Protobuf via gRPC.
        username: The user name of the Basic Auth if authentication is
            required.
        password: The password of the Basic Auth if authentication is
            required.
        insecure: True if collector has no encryption or authentication
        credentials: Credentials for server authentication.
        transport_format: Transport format for exporting spans to collector.
        max_tag_value_length: Max length string attribute values can have. Set to None to disable.
        udp_split_oversized_batches: Re-emit oversized batches in smaller chunks.
    """

    def __init__(
        self,
        service_name: str,
        agent_host_name: Optional[str] = None,
        agent_port: Optional[int] = None,
        collector_endpoint: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        insecure: Optional[bool] = None,
        credentials: Optional[ChannelCredentials] = None,
        transport_format: Optional[str] = None,
        max_tag_value_length: Optional[int] = None,
        udp_split_oversized_batches: bool = None,
    ):
        self.service_name = service_name
        self._max_tag_value_length = max_tag_value_length
        self.agent_host_name = _parameter_setter(
            param=agent_host_name,
            env_variable=environ.get(OTEL_EXPORTER_JAEGER_AGENT_HOST),
            default=DEFAULT_AGENT_HOST_NAME,
        )

        environ_agent_port = environ.get(OTEL_EXPORTER_JAEGER_AGENT_PORT)
        environ_agent_port = (
            int(environ_agent_port) if environ_agent_port is not None else None
        )

        self.agent_port = _parameter_setter(
            param=agent_port,
            env_variable=environ_agent_port,
            default=DEFAULT_AGENT_PORT,
        )
        self.udp_split_oversized_batches = _parameter_setter(
            param=udp_split_oversized_batches,
            env_variable=environ.get(
                OTEL_EXPORTER_JAEGER_AGENT_SPLIT_OVERSIZED_BATCHES
            ),
            default=False,
        )
        self._agent_client = AgentClientUDP(
            host_name=self.agent_host_name,
            port=self.agent_port,
            split_oversized_batches=self.udp_split_oversized_batches,
        )
        self.collector_endpoint = _parameter_setter(
            param=collector_endpoint,
            env_variable=environ.get(OTEL_EXPORTER_JAEGER_ENDPOINT),
            default=None,
        )
        self.username = _parameter_setter(
            param=username,
            env_variable=environ.get(OTEL_EXPORTER_JAEGER_USER),
            default=None,
        )
        self.password = _parameter_setter(
            param=password,
            env_variable=environ.get(OTEL_EXPORTER_JAEGER_PASSWORD),
            default=None,
        )
        self._collector = None
        self._grpc_client = None
        self.insecure = util._get_insecure(insecure)
        self.credentials = util._get_credentials(credentials)
        self.transport_format = (
            transport_format.lower()
            if transport_format
            else TRANSPORT_FORMAT_THRIFT
        )

    @property
    def _collector_grpc_client(self) -> Optional[CollectorServiceStub]:
        if self.transport_format != TRANSPORT_FORMAT_PROTOBUF:
            return None

        endpoint = self.collector_endpoint or DEFAULT_GRPC_COLLECTOR_ENDPOINT

        if self._grpc_client is None:
            if self.insecure:
                self._grpc_client = CollectorServiceStub(
                    insecure_channel(endpoint)
                )
            else:
                self._grpc_client = CollectorServiceStub(
                    secure_channel(endpoint, self.credentials)
                )
        return self._grpc_client

    @property
    def _collector_http_client(self) -> Optional[Collector]:
        if self._collector is not None:
            return self._collector

        if (
            self.collector_endpoint is None
            or self.transport_format != TRANSPORT_FORMAT_THRIFT
        ):
            return None

        auth = None
        if self.username is not None and self.password is not None:
            auth = (self.username, self.password)

        self._collector = Collector(
            thrift_url=self.collector_endpoint, auth=auth
        )
        return self._collector

    def export(self, spans) -> SpanExportResult:
        translator = Translate(spans)
        if self.transport_format == TRANSPORT_FORMAT_PROTOBUF:
            pb_translator = ProtobufTranslator(
                self.service_name, self._max_tag_value_length
            )
            jaeger_spans = translator._translate(pb_translator)
            batch = model_pb2.Batch(spans=jaeger_spans)
            request = PostSpansRequest(batch=batch)
            self._collector_grpc_client.PostSpans(request)
        else:
            thrift_translator = ThriftTranslator(self._max_tag_value_length)
            jaeger_spans = translator._translate(thrift_translator)
            batch = jaeger_thrift.Batch(
                spans=jaeger_spans,
                process=jaeger_thrift.Process(serviceName=self.service_name),
            )
            if self._collector_http_client is not None:
                self._collector_http_client.submit(batch)
            else:
                self._agent_client.emit(batch)

        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


def _parameter_setter(param, env_variable, default):
    """Returns value according to the provided data.

    Args:
        param: Constructor parameter value
        env_variable: Environment variable related to the parameter
        default: Constructor parameter default value
    """
    if param is None:
        res = env_variable or default
    else:
        res = param

    return res
