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

OpenTelemetry Jaeger Thrift Exporter
------------------------------------

The **OpenTelemetry Jaeger Thrift Exporter** allows to export `OpenTelemetry`_ traces to `Jaeger`_.
This exporter always sends traces to the configured agent using the Thrift compact protocol over UDP.
When it is not feasible to deploy Jaeger Agent next to the application, for example, when the
application code is running as Lambda function, a collector can be configured to send spans
using Thrift over HTTP. If both agent and collector are configured, the exporter sends traces
only to the collector to eliminate the duplicate entries.

Usage
-----

.. code:: python

    from opentelemetry import trace
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    trace.set_tracer_provider(
    TracerProvider(
            resource=Resource.create({SERVICE_NAME: "my-helloworld-service"})
        )
    )
    tracer = trace.get_tracer(__name__)

    # create a JaegerExporter
    jaeger_exporter = JaegerExporter(
        # configure agent
        agent_host_name='localhost',
        agent_port=6831,
        # optional: configure also collector
        # collector_endpoint='http://localhost:14268/api/traces?format=jaeger.thrift',
        # username=xxxx, # optional
        # password=xxxx, # optional
        # max_tag_value_length=None # optional
    )

    # Create a BatchSpanProcessor and add the exporter to it
    span_processor = BatchSpanProcessor(jaeger_exporter)

    # add to the tracer
    trace.get_tracer_provider().add_span_processor(span_processor)

    with tracer.start_as_current_span('foo'):
        print('Hello world!')

You can configure the exporter with the following environment variables:

- :envvar:`OTEL_EXPORTER_JAEGER_USER`
- :envvar:`OTEL_EXPORTER_JAEGER_PASSWORD`
- :envvar:`OTEL_EXPORTER_JAEGER_ENDPOINT`
- :envvar:`OTEL_EXPORTER_JAEGER_AGENT_PORT`
- :envvar:`OTEL_EXPORTER_JAEGER_AGENT_HOST`
- :envvar:`OTEL_EXPORTER_JAEGER_AGENT_SPLIT_OVERSIZED_BATCHES`
- :envvar:`OTEL_EXPORTER_JAEGER_TIMEOUT`

API
---
.. _Jaeger: https://www.jaegertracing.io/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
"""
# pylint: disable=protected-access

import logging
from os import environ
from typing import Optional

from deprecated import deprecated

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift.gen.jaeger import (
    Collector as jaeger_thrift,
)
from opentelemetry.exporter.jaeger.thrift.send import AgentClientUDP, Collector
from opentelemetry.exporter.jaeger.thrift.translate import (
    ThriftTranslator,
    Translate,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_JAEGER_AGENT_HOST,
    OTEL_EXPORTER_JAEGER_AGENT_PORT,
    OTEL_EXPORTER_JAEGER_AGENT_SPLIT_OVERSIZED_BATCHES,
    OTEL_EXPORTER_JAEGER_ENDPOINT,
    OTEL_EXPORTER_JAEGER_PASSWORD,
    OTEL_EXPORTER_JAEGER_TIMEOUT,
    OTEL_EXPORTER_JAEGER_USER,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

DEFAULT_AGENT_HOST_NAME = "localhost"
DEFAULT_AGENT_PORT = 6831
DEFAULT_EXPORT_TIMEOUT = 10

logger = logging.getLogger(__name__)


class JaegerExporter(SpanExporter):
    """Jaeger span exporter for OpenTelemetry.

    Args:
        agent_host_name: The host name of the Jaeger-Agent.
        agent_port: The port of the Jaeger-Agent.
        collector_endpoint: The endpoint of the Jaeger collector that uses
            Thrift over HTTP/HTTPS.
        username: The user name of the Basic Auth if authentication is
            required.
        password: The password of the Basic Auth if authentication is
            required.
        max_tag_value_length: Max length string attribute values can have. Set to None to disable.
        udp_split_oversized_batches: Re-emit oversized batches in smaller chunks.
        timeout: Maximum time the Jaeger exporter should wait for each batch export.
    """

    @deprecated(
        version="1.16.0",
        reason="Since v1.35, the Jaeger supports OTLP natively. Please use the OTLP exporter instead. Support for this exporter will end July 2023.",
    )
    def __init__(
        self,
        agent_host_name: Optional[str] = None,
        agent_port: Optional[int] = None,
        collector_endpoint: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        max_tag_value_length: Optional[int] = None,
        udp_split_oversized_batches: bool = None,
        timeout: Optional[int] = None,
    ):
        self._max_tag_value_length = max_tag_value_length
        self.agent_host_name = agent_host_name or environ.get(
            OTEL_EXPORTER_JAEGER_AGENT_HOST, DEFAULT_AGENT_HOST_NAME
        )

        self.agent_port = agent_port or int(
            environ.get(OTEL_EXPORTER_JAEGER_AGENT_PORT, DEFAULT_AGENT_PORT)
        )

        self._timeout = timeout or int(
            environ.get(OTEL_EXPORTER_JAEGER_TIMEOUT, DEFAULT_EXPORT_TIMEOUT)
        )

        self.udp_split_oversized_batches = udp_split_oversized_batches or bool(
            environ.get(OTEL_EXPORTER_JAEGER_AGENT_SPLIT_OVERSIZED_BATCHES)
        )
        self._agent_client = AgentClientUDP(
            host_name=self.agent_host_name,
            port=self.agent_port,
            split_oversized_batches=self.udp_split_oversized_batches,
        )
        self.collector_endpoint = collector_endpoint or environ.get(
            OTEL_EXPORTER_JAEGER_ENDPOINT
        )
        self.username = username or environ.get(OTEL_EXPORTER_JAEGER_USER)
        self.password = password or environ.get(OTEL_EXPORTER_JAEGER_PASSWORD)
        self._collector = None
        tracer_provider = trace.get_tracer_provider()
        self.service_name = (
            tracer_provider.resource.attributes[SERVICE_NAME]
            if getattr(tracer_provider, "resource", None)
            else Resource.create().attributes.get(SERVICE_NAME)
        )

    @property
    def _collector_http_client(self) -> Optional[Collector]:
        if self._collector is not None:
            return self._collector

        if self.collector_endpoint is None:
            return None

        auth = None
        if self.username is not None and self.password is not None:
            auth = (self.username, self.password)

        # Thrift HTTP Client expects timeout in millis
        timeout_in_millis = self._timeout * 1000.0
        self._collector = Collector(
            thrift_url=self.collector_endpoint,
            auth=auth,
            timeout_in_millis=timeout_in_millis,
        )
        return self._collector

    def export(self, spans) -> SpanExportResult:
        # Populate service_name from first span
        # We restrict any SpanProcessor to be only associated with a single
        # TracerProvider, so it is safe to assume that all Spans in a single
        # batch all originate from one TracerProvider (and in turn have all
        # the same service.name)
        if spans:
            service_name = spans[0].resource.attributes.get(SERVICE_NAME)
            if service_name:
                self.service_name = service_name
        translator = Translate(spans)
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

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
