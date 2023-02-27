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

OpenTelemetry Jaeger Protobuf Exporter
--------------------------------------

The **OpenTelemetry Jaeger Protobuf Exporter** allows to export `OpenTelemetry`_ traces to `Jaeger`_.
This exporter always sends traces to the configured agent using Protobuf via gRPC.

Usage
-----

.. code:: python

    from opentelemetry import trace
    from opentelemetry.exporter.jaeger.proto.grpc import JaegerExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    # create a JaegerExporter
    jaeger_exporter = JaegerExporter(
        # optional: configure collector
        # collector_endpoint='localhost:14250',
        # insecure=True, # optional
        # credentials=xxx # optional channel creds
        # max_tag_value_length=None # optional
    )

    # Create a BatchSpanProcessor and add the exporter to it
    span_processor = BatchSpanProcessor(jaeger_exporter)

    # add to the tracer
    trace.get_tracer_provider().add_span_processor(span_processor)

    with tracer.start_as_current_span('foo'):
        print('Hello world!')

You can configure the exporter with the following environment variables:

- :envvar:`OTEL_EXPORTER_JAEGER_ENDPOINT`
- :envvar:`OTEL_EXPORTER_JAEGER_CERTIFICATE`
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

from grpc import ChannelCredentials, RpcError, insecure_channel, secure_channel

from opentelemetry import trace
from opentelemetry.exporter.jaeger.proto.grpc import util
from opentelemetry.exporter.jaeger.proto.grpc.gen import model_pb2
from opentelemetry.exporter.jaeger.proto.grpc.gen.collector_pb2 import (
    PostSpansRequest,
)
from opentelemetry.exporter.jaeger.proto.grpc.gen.collector_pb2_grpc import (
    CollectorServiceStub,
)
from opentelemetry.exporter.jaeger.proto.grpc.translate import (
    ProtobufTranslator,
    Translate,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_JAEGER_ENDPOINT,
    OTEL_EXPORTER_JAEGER_TIMEOUT,
    OTEL_EXPORTER_JAEGER_GRPC_INSECURE,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

DEFAULT_GRPC_COLLECTOR_ENDPOINT = "localhost:14250"
DEFAULT_EXPORT_TIMEOUT = 10

logger = logging.getLogger(__name__)


class JaegerExporter(SpanExporter):
    """Jaeger span exporter for OpenTelemetry.

    Args:
        collector_endpoint: The endpoint of the Jaeger collector that uses
            Protobuf via gRPC.
        insecure: True if collector has no encryption or authentication
        credentials: Credentials for server authentication.
        max_tag_value_length: Max length string attribute values can have. Set to None to disable.
        timeout: Maximum time the Jaeger exporter should wait for each batch export.
    """

    @deprecated(
        version="1.16.0",
        reason="Since v1.35, the Jaeger supports OTLP natively. Please use the OTLP exporter instead. Support for this exporter will end July 2023.",
    )
    def __init__(
        self,
        collector_endpoint: Optional[str] = None,
        insecure: Optional[bool] = None,
        credentials: Optional[ChannelCredentials] = None,
        max_tag_value_length: Optional[int] = None,
        timeout: Optional[int] = None,
    ):
        self._max_tag_value_length = max_tag_value_length

        self.collector_endpoint = collector_endpoint or environ.get(
            OTEL_EXPORTER_JAEGER_ENDPOINT, DEFAULT_GRPC_COLLECTOR_ENDPOINT
        )
        self.insecure = (
            insecure
            or environ.get(OTEL_EXPORTER_JAEGER_GRPC_INSECURE, "")
            .strip()
            .lower()
            == "true"
        )
        self._timeout = timeout or int(
            environ.get(OTEL_EXPORTER_JAEGER_TIMEOUT, DEFAULT_EXPORT_TIMEOUT)
        )
        self._grpc_client = None
        self.credentials = util._get_credentials(credentials)
        tracer_provider = trace.get_tracer_provider()
        self.service_name = (
            tracer_provider.resource.attributes[SERVICE_NAME]
            if getattr(tracer_provider, "resource", None)
            else Resource.create().attributes.get(SERVICE_NAME)
        )

    @property
    def _collector_grpc_client(self) -> Optional[CollectorServiceStub]:

        if self._grpc_client is None:
            if self.insecure:
                self._grpc_client = CollectorServiceStub(
                    insecure_channel(self.collector_endpoint)
                )
            else:
                self._grpc_client = CollectorServiceStub(
                    secure_channel(self.collector_endpoint, self.credentials)
                )
        return self._grpc_client

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
        pb_translator = ProtobufTranslator(
            self.service_name, self._max_tag_value_length
        )
        jaeger_spans = translator._translate(pb_translator)
        batch = model_pb2.Batch(spans=jaeger_spans)
        request = PostSpansRequest(batch=batch)
        try:
            self._collector_grpc_client.PostSpans(
                request, timeout=self._timeout
            )
            return SpanExportResult.SUCCESS
        except RpcError as error:
            logger.warning(
                "Failed to export batch. Status code: %s", error.code()
            )
            return SpanExportResult.FAILURE

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
