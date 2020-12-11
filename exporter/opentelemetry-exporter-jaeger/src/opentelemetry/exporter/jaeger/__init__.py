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
This exporter always send traces to the configured agent using Thrift compact protocol over UDP.
An optional collector can be configured, in this case Thrift binary protocol over HTTP is used.
gRPC is still not supported by this implementation.

Usage
-----

.. code:: python

    from opentelemetry import trace
    from opentelemetry.exporter import jaeger
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    # create a JaegerSpanExporter
    jaeger_exporter = jaeger.JaegerSpanExporter(
        service_name='my-helloworld-service',
        # configure agent
        agent_host_name='localhost',
        agent_port=6831,
        # optional: configure also collector
        # collector_endpoint='http://localhost:14268/api/traces?format=jaeger.thrift',
        # username=xxxx, # optional
        # password=xxxx, # optional
    )

    # Create a BatchExportSpanProcessor and add the exporter to it
    span_processor = BatchExportSpanProcessor(jaeger_exporter)

    # add to the tracer
    trace.get_tracer_provider().add_span_processor(span_processor)

    with tracer.start_as_current_span('foo'):
        print('Hello world!')

API
---
.. _Jaeger: https://www.jaegertracing.io/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
"""

import base64
import logging
import socket
from typing import Optional, Union

from grpc import (
    ChannelCredentials,
    insecure_channel,
    secure_channel,
    ssl_channel_credentials,
)
from thrift.protocol import TBinaryProtocol, TCompactProtocol
from thrift.transport import THttpClient, TTransport

import opentelemetry.exporter.jaeger.gen.model_pb2 as model_pb2
from opentelemetry.configuration import Configuration
from opentelemetry.exporter.jaeger.gen.agent import Agent as agent
from opentelemetry.exporter.jaeger.gen.collector_pb2 import PostSpansRequest
from opentelemetry.exporter.jaeger.gen.collector_pb2_grpc import (
    CollectorServiceStub,
)
from opentelemetry.exporter.jaeger.gen.jaeger import Collector as jaeger
from opentelemetry.exporter.jaeger.send.thrift import AgentClientUDP, Collector
from opentelemetry.exporter.jaeger.translate import thrift, protobuf
from opentelemetry.sdk.trace.export import Span, SpanExporter, SpanExportResult
from opentelemetry.trace import SpanKind
from opentelemetry.trace.status import StatusCode

DEFAULT_AGENT_HOST_NAME = "localhost"
DEFAULT_AGENT_PORT = 6831

UDP_PACKET_MAX_LENGTH = 65000

TRANSPORT_FORMAT_THRIFT = "thrift"
TRANSPORT_FORMAT_PROTOBUF = "protobuf"

logger = logging.getLogger(__name__)


class JaegerSpanExporter(SpanExporter):
    """Jaeger span exporter for OpenTelemetry.

    Args:
        service_name: Service that logged an annotation in a trace.Classifier
            when query for spans.
        agent_host_name: The host name of the Jaeger-Agent.
        agent_port: The port of the Jaeger-Agent.
        collector_endpoint: The endpoint of the Jaeger-Collector HTTP/HTTPS Thrift.
        username: The user name of the Basic Auth if authentication is
            required.
        password: The password of the Basic Auth if authentication is
            required.
        insecure: Connection type
        credentials: Credentials for server authentication
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
        transport_format: Union[
            TRANSPORT_FORMAT_THRIFT, TRANSPORT_FORMAT_PROTOBUF
        ] = None,
    ):
        self.service_name = service_name
        self.agent_host_name = _parameter_setter(
            param=agent_host_name,
            env_variable=Configuration().EXPORTER_JAEGER_AGENT_HOST,
            default=DEFAULT_AGENT_HOST_NAME,
        )
        self.agent_port = int(
            _parameter_setter(
                param=agent_port,
                env_variable=Configuration().EXPORTER_JAEGER_AGENT_PORT,
                default=DEFAULT_AGENT_PORT,
            )
        )
        self._agent_client = None
        self.collector_endpoint = _parameter_setter(
            param=collector_endpoint,
            env_variable=Configuration().EXPORTER_JAEGER_ENDPOINT,
            default=None,
        )
        self.username = _parameter_setter(
            param=username,
            env_variable=Configuration().EXPORTER_JAEGER_USER,
            default=None,
        )
        self.password = _parameter_setter(
            param=password,
            env_variable=Configuration().EXPORTER_JAEGER_PASSWORD,
            default=None,
        )
        self._collector = None
        self._grpc_client = None
        self.insecure = insecure
        self.credentials = credentials
        self.transport_format = transport_format

    @property
    def agent_client(self) -> AgentClientUDP:
        if self._agent_client is None:
            self._agent_client = AgentClientUDP(
                host_name=self.agent_host_name, port=self.agent_port
            )
        return self._agent_client

    @property
    def grpc_client(self) -> Optional[CollectorServiceStub]:
        if not self.collector_endpoint:
            return None

        if self._grpc_client is None:
            if self.insecure:
                self._grpc_client = CollectorServiceStub(
                    insecure_channel(self.collector_endpoint)
                )
            else:
                creds = self.credentials
                if creds is None:
                    creds = ssl_channel_credentials()
                self._grpc_client = CollectorServiceStub(
                    secure_channel(self.collector_endpoint, creds)
                )
        return self._grpc_client

    @property
    def collector(self) -> Optional[Collector]:
        if self._collector is not None:
            return self._collector

        if self.collector_endpoint is None:
            return None

        auth = None
        if self.username is not None and self.password is not None:
            auth = (self.username, self.password)

        self._collector = Collector(
            thrift_url=self.collector_endpoint, auth=auth
        )
        return self._collector

    def export(self, spans):
        if self.transport_format == TRANSPORT_FORMAT_PROTOBUF:
            spans = protobuf._to_jaeger(spans)
            batch = model_pb2.Batch(spans)
            request = PostSpansRequest(batch=batch)
            self._grpc_client.PostSpans(request)
        else:
            jaeger_spans = thrift._to_jaeger(spans)
            batch = jaeger.Batch(
                spans=jaeger_spans,
                process=jaeger.Process(serviceName=self.service_name),
            )
            if self.collector is not None:
                self.collector.submit(batch)
            else:
                self.agent_client.emit(batch)

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
