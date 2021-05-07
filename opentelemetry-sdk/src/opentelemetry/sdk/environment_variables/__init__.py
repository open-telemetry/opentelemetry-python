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

OTEL_RESOURCE_ATTRIBUTES = "OTEL_RESOURCE_ATTRIBUTES"
"""
.. envvar:: OTEL_RESOURCE_ATTRIBUTES

The :envvar:`OTEL_RESOURCE_ATTRIBUTES` environment variable allows resource
attributes to be passed to the SDK at process invocation. The attributes from
:envvar:`OTEL_RESOURCE_ATTRIBUTES` are merged with those passed to
`Resource.create`, meaning :envvar:`OTEL_RESOURCE_ATTRIBUTES` takes *lower*
priority. Attributes should be in the format ``key1=value1,key2=value2``.
Additional details are available `in the specification
<https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/resource/sdk.md#specifying-resource-information-via-an-environment-variable>`__.

.. code-block:: console

    $ OTEL_RESOURCE_ATTRIBUTES="service.name=shoppingcard,will_be_overridden=foo" python - <<EOF
    import pprint
    from opentelemetry.sdk.resources import Resource
    pprint.pprint(Resource.create({"will_be_overridden": "bar"}).attributes)
    EOF
    {'service.name': 'shoppingcard',
    'telemetry.sdk.language': 'python',
    'telemetry.sdk.name': 'opentelemetry',
    'telemetry.sdk.version': '0.13.dev0',
    'will_be_overridden': 'bar'}
"""

OTEL_LOG_LEVEL = "OTEL_LOG_LEVEL"
"""
.. envvar:: OTEL_LOG_LEVEL
"""

OTEL_TRACES_SAMPLER = "OTEL_TRACES_SAMPLER"
"""
.. envvar:: OTEL_TRACES_SAMPLER
"""

OTEL_TRACES_SAMPLER_ARG = "OTEL_TRACES_SAMPLER_ARG"
"""
.. envvar:: OTEL_TRACES_SAMPLER_ARG
"""

OTEL_BSP_SCHEDULE_DELAY = "OTEL_BSP_SCHEDULE_DELAY"
"""
.. envvar:: OTEL_BSP_SCHEDULE_DELAY
"""

OTEL_BSP_EXPORT_TIMEOUT = "OTEL_BSP_EXPORT_TIMEOUT"
"""
.. envvar:: OTEL_BSP_EXPORT_TIMEOUT
"""

OTEL_BSP_MAX_QUEUE_SIZE = "OTEL_BSP_MAX_QUEUE_SIZE"
"""
.. envvar:: OTEL_BSP_MAX_QUEUE_SIZE
"""

OTEL_BSP_MAX_EXPORT_BATCH_SIZE = "OTEL_BSP_MAX_EXPORT_BATCH_SIZE"
"""
.. envvar:: OTEL_BSP_MAX_EXPORT_BATCH_SIZE
"""

OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT = "OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT"
"""
.. envvar:: OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT
"""

OTEL_SPAN_EVENT_COUNT_LIMIT = "OTEL_SPAN_EVENT_COUNT_LIMIT"
"""
.. envvar:: OTEL_SPAN_EVENT_COUNT_LIMIT
"""

OTEL_SPAN_LINK_COUNT_LIMIT = "OTEL_SPAN_LINK_COUNT_LIMIT"
"""
.. envvar:: OTEL_SPAN_LINK_COUNT_LIMIT
"""

OTEL_EXPORTER_JAEGER_AGENT_HOST = "OTEL_EXPORTER_JAEGER_AGENT_HOST"
"""
.. envvar:: OTEL_EXPORTER_JAEGER_AGENT_HOST
"""

OTEL_EXPORTER_JAEGER_AGENT_PORT = "OTEL_EXPORTER_JAEGER_AGENT_PORT"
"""
.. envvar:: OTEL_EXPORTER_JAEGER_AGENT_PORT
"""

OTEL_EXPORTER_JAEGER_ENDPOINT = "OTEL_EXPORTER_JAEGER_ENDPOINT"
"""
.. envvar:: OTEL_EXPORTER_JAEGER_ENDPOINT
"""

OTEL_EXPORTER_JAEGER_USER = "OTEL_EXPORTER_JAEGER_USER"
"""
.. envvar:: OTEL_EXPORTER_JAEGER_USER
"""

OTEL_EXPORTER_JAEGER_PASSWORD = "OTEL_EXPORTER_JAEGER_PASSWORD"
"""
.. envvar:: OTEL_EXPORTER_JAEGER_PASSWORD
"""


OTEL_EXPORTER_ZIPKIN_ENDPOINT = "OTEL_EXPORTER_ZIPKIN_ENDPOINT"
"""
.. envvar:: OTEL_EXPORTER_ZIPKIN_ENDPOINT

Zipkin collector endpoint to which the exporter will send data. This may
include a path (e.g. ``http://example.com:9411/api/v2/spans``).
"""

OTEL_EXPORTER_ZIPKIN_TIMEOUT = "OTEL_EXPORTER_ZIPKIN_TIMEOUT"
"""
.. envvar:: OTEL_EXPORTER_ZIPKIN_TIMEOUT

Maximum time the Zipkin exporter will wait for each batch export, the default
timeout is 10s.
"""

OTEL_EXPORTER_OTLP_PROTOCOL = "OTEL_EXPORTER_OTLP_PROTOCOL"
"""
.. envvar:: OTEL_EXPORTER_OTLP_PROTOCOL
"""

OTEL_EXPORTER_OTLP_CERTIFICATE = "OTEL_EXPORTER_OTLP_CERTIFICATE"
"""
.. envvar:: OTEL_EXPORTER_OTLP_CERTIFICATE
"""

OTEL_EXPORTER_OTLP_HEADERS = "OTEL_EXPORTER_OTLP_HEADERS"
"""
.. envvar:: OTEL_EXPORTER_OTLP_HEADERS
"""


OTEL_EXPORTER_OTLP_COMPRESSION = "OTEL_EXPORTER_OTLP_COMPRESSION"
"""
.. envvar:: OTEL_EXPORTER_OTLP_COMPRESSION

Specifies a gRPC compression method to be used in the OTLP exporters.
Possible values are:

- ``gzip`` corresponding to `grpc.Compression.Gzip`.
- ``deflate`` corresponding to `grpc.Compression.Deflate`.

If no ``OTEL_EXPORTER_OTLP_*COMPRESSION`` environment variable is present or
``compression`` argument passed to the exporter, the default
`grpc.Compression.NoCompression` will be used. Additional details are
available `in the specification
<https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/protocol/exporter.md#opentelemetry-protocol-exporter>`__.
"""

OTEL_EXPORTER_OTLP_TIMEOUT = "OTEL_EXPORTER_OTLP_TIMEOUT"
"""
.. envvar:: OTEL_EXPORTER_OTLP_TIMEOUT
"""

OTEL_EXPORTER_OTLP_ENDPOINT = "OTEL_EXPORTER_OTLP_ENDPOINT"
"""
.. envvar:: OTEL_EXPORTER_OTLP_ENDPOINT
"""

OTEL_EXPORTER_OTLP_TRACES_ENDPOINT = "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"
"""
.. envvar:: OTEL_EXPORTER_OTLP_TRACES_ENDPOINT
"""

OTEL_EXPORTER_OTLP_TRACES_PROTOCOL = "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL"
"""
.. envvar:: OTEL_EXPORTER_OTLP_TRACES_PROTOCOL
"""

OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE = "OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE"
"""
.. envvar:: OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE
"""

OTEL_EXPORTER_OTLP_TRACES_HEADERS = "OTEL_EXPORTER_OTLP_TRACES_HEADERS"
"""
.. envvar:: OTEL_EXPORTER_OTLP_TRACES_HEADERS
"""


OTEL_EXPORTER_OTLP_TRACES_COMPRESSION = "OTEL_EXPORTER_OTLP_TRACES_COMPRESSION"
"""
.. envvar:: OTEL_EXPORTER_OTLP_TRACES_COMPRESSION

Same as :envvar:`OTEL_EXPORTER_OTLP_COMPRESSION` but only for the span
exporter. If both are present, this takes higher precendence.
"""

OTEL_EXPORTER_OTLP_TRACES_TIMEOUT = "OTEL_EXPORTER_OTLP_TRACES_TIMEOUT"
"""
.. envvar:: OTEL_EXPORTER_OTLP_TRACES_TIMEOUT
"""

OTEL_EXPORTER_JAEGER_CERTIFICATE = "OTEL_EXPORTER_JAEGER_CERTIFICATE"
"""
.. envvar:: OTEL_EXPORTER_JAEGER_CERTIFICATE
"""

OTEL_EXPORTER_JAEGER_AGENT_SPLIT_OVERSIZED_BATCHES = (
    "OTEL_EXPORTER_JAEGER_AGENT_SPLIT_OVERSIZED_BATCHES"
)
"""
.. envvar:: OTEL_EXPORTER_JAEGER_AGENT_SPLIT_OVERSIZED_BATCHES
"""

OTEL_SERVICE_NAME = "OTEL_SERVICE_NAME"
"""
.. envvar:: OTEL_SERVICE_NAME

Convenience environment variable for setting the service name resource attribute.
The following two environment variables have the same effect

.. code-block:: console

    OTEL_SERVICE_NAME=my-python-service

    OTEL_RESOURCE_ATTRIBUTES=service.name=my-python-service


If both are set, :envvar:`OTEL_SERVICE_NAME` takes precedence.
"""
