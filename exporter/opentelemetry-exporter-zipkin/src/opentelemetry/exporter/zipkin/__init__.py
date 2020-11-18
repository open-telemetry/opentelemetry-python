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
This library allows to export tracing data to `Zipkin <https://zipkin.io/>`_.

Usage
-----

The **OpenTelemetry Zipkin Exporter** allows to export `OpenTelemetry`_ traces to `Zipkin`_.
This exporter always send traces to the configured Zipkin collector using HTTP.


.. _Zipkin: https://zipkin.io/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
.. _Specification: https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/sdk-environment-variables.md#zipkin-exporter

.. envvar:: OTEL_EXPORTER_ZIPKIN_SERVICE_NAME
.. envvar:: OTEL_EXPORTER_ZIPKIN_ENDPOINT
.. envvar:: OTEL_EXPORTER_ZIPKIN_ENCODING

.. code:: python

    from opentelemetry import trace
    from opentelemetry.exporter import zipkin
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    # create an exporter with defaults
    zipkin_exporter = zipkin.ZipkinSpanExporter("my-helloworld-service")

    # create an exporter with explicit endpoint and encoding.
    # additional import needed:
    #     from opentelemetry.exporter.zipkin.encoder import Encoding
    #
    zipkin_exporter = zipkin.ZipkinSpanExporter(
        "my-helloworld-service",
        endpoint="http://localhost:9411/api/v2/spans",
        encoding=Encoding.PROTOBUF
    )

    # create an advanced exporter with explicit encoder and sender.
    # additional imports needed:
    #     from opentelemetry.exporter.zipkin.encoder import Encoding
    #     from opentelemetry.exporter.zipkin.encoder.protobuf import (
    #         ProtobufEncoder
    #     )
    #     from opentelemetry.exporter.zipkin.endpoint import Endpoint
    #     from opentelemetry.exporter.zipkin.sender.http import HttpSender
    #
    zipkin_exporter = zipkin.ZipkinSpanExporter(
        encoder=ProtobufEncoder(
            Endpoint("my_service"),
            max_tag_value_length=256
        ),
        sender=HttpSender(
            endpoint="http://remote.endpoint.com:9411/api/v2/spans",
            encoding=Encoding.PROTOBUF,
        ),
    )

    # Create a BatchExportSpanProcessor and add the exporter to it
    span_processor = BatchExportSpanProcessor(zipkin_exporter)

    # add to the tracer
    trace.get_tracer_provider().add_span_processor(span_processor)

    with tracer.start_as_current_span("foo"):
        print("Hello world!")

The exporter supports the following environment variables for configuration:

:envvar:`OTEL_EXPORTER_ZIPKIN_SERVICE_NAME`: Label of the remote node in the
service graph, such as "favstar". Avoid names with variables or unique
identifiers embedded. Defaults to "unknown". This is a primary label for trace
lookup and aggregation, so it should be intuitive and consistent. Many use a
name from service discovery.

:envvar:`OTEL_EXPORTER_ZIPKIN_ENDPOINT`: target to which the exporter will
send data. This may include a path (e.g. http://example.com:9411/api/v2/spans).

:envvar:`OTEL_EXPORTER_ZIPKIN_ENCODING`: transport interchange format
encoder to use when sending data. Currently only Zipkin's v2 json and protobuf
formats are supported, with v2 json being the default.

API
---
"""

from typing import Sequence

from opentelemetry.configuration import Configuration
from opentelemetry.exporter.zipkin.encoder import Encoder, Encoding
from opentelemetry.exporter.zipkin.encoder.v1.json import JsonV1Encoder
from opentelemetry.exporter.zipkin.encoder.v2.json import JsonV2Encoder
from opentelemetry.exporter.zipkin.encoder.v2.protobuf import ProtobufEncoder
from opentelemetry.exporter.zipkin.endpoint import Endpoint
from opentelemetry.exporter.zipkin.sender.http import Sender, HttpSender
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import Span

DEFAULT_SERVICE_NAME = "unknown"
DEFAULT_ENDPOINT = "http://localhost:9411/api/v2/spans"
DEFAULT_ENCODING = Encoding.V2_JSON


class ZipkinSpanExporter(SpanExporter):
    """Zipkin span exporter for OpenTelemetry.

    Attributes:
        encoder: handles conversion of span data into a specified
          transport format (e.g. protobuf)
        sender: handles transport of encoded spans over a given
          protocol (e.g. http)
    """

    def __init__(
        self,
        service_name: str = None,
        endpoint: str = None,
        encoding: Encoding = None,
        encoder: Encoder = None,
        sender: Sender = None,
    ):
        """Instantiates a ZipkinSpanExporter.

        :param service_name: Lowercase label of this node in the service
        graph, such as "favstar". This is a primary label for trace lookup
        and aggregation, so it should be intuitive and consistent. Many
        use a name from service discovery.
        :param endpoint: the zipkin endpoint where data will be exported (ex:
        "http://localhost:9411/api/v2/spans"). This param is ignored if
        the sender param is also provided since the sender will already
        have an endpoint defined.
        :param encoding: defines the encoding to use for both the encoder and
        sender. This param will be ignored by an encoder or sender also
        provided as a param since they will have already defined their
        encoding.
        :param encoder: handles conversion of span data into a specified
        transport format (e.g. protobuf). If provided along with the
        'encoding' param, the encoder will take precedence and ignore the
        'encoding' param.
        :param sender: handles transport of encoded spans over a given
        protocol (e.g. http). If provided along with the 'encoding' and/or
        'endpoint' params, the sender will take precedence and ignore those
        params.
        """
        if encoding is None:
            env_encoding = Configuration().EXPORTER_ZIPKIN_ENCODING
            if env_encoding is not None:
                encoding = Encoding(env_encoding)
            else:
                encoding = DEFAULT_ENCODING

        if encoder is not None:
            self.encoder = encoder
        else:
            if service_name is None:
                service_name = (
                    Configuration().EXPORTER_ZIPKIN_SERVICE_NAME
                    or DEFAULT_SERVICE_NAME
                )
            # TODO: add logic to determine primary ipv4 and ipv6 addresses to
            #  pass into Endpoint constructor.
            local_endpoint = Endpoint(service_name)
            if encoding == Encoding.V1_JSON:
                self.encoder = JsonV1Encoder(local_endpoint)
            elif encoding == Encoding.V2_JSON:
                self.encoder = JsonV2Encoder(local_endpoint)
            elif encoding == Encoding.V2_PROTOBUF:
                self.encoder = ProtobufEncoder(local_endpoint)

        if sender is not None:
            self.sender = sender
        else:
            if endpoint is None:
                endpoint = (
                    Configuration().EXPORTER_ZIPKIN_ENDPOINT
                    or DEFAULT_ENDPOINT
                )
            self.sender = HttpSender(endpoint, encoding)

    def export(self, spans: Sequence[Span]) -> SpanExportResult:
        return self.sender.send(self.encoder.encode(spans))

    def shutdown(self) -> None:
        pass
