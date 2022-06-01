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

The :envvar:`OTEL_LOG_LEVEL` environment variable sets the log level used by the SDK logger
Default: "info"
"""

OTEL_TRACES_SAMPLER = "OTEL_TRACES_SAMPLER"
"""
.. envvar:: OTEL_TRACES_SAMPLER

The :envvar:`OTEL_TRACES_SAMPLER` environment variable sets the sampler to be used for traces.
Sampling is a mechanism to control the noise introduced by OpenTelemetry by reducing the number
of traces collected and sent to the backend
Default: "parentbased_always_on"
"""

OTEL_TRACES_SAMPLER_ARG = "OTEL_TRACES_SAMPLER_ARG"
"""
.. envvar:: OTEL_TRACES_SAMPLER_ARG

The :envvar:`OTEL_TRACES_SAMPLER_ARG` environment variable will only be used if OTEL_TRACES_SAMPLER is set.
Each Sampler type defines its own expected input, if any.
Invalid or unrecognized input is ignored,
i.e. the SDK behaves as if OTEL_TRACES_SAMPLER_ARG is not set.
"""

OTEL_BSP_SCHEDULE_DELAY = "OTEL_BSP_SCHEDULE_DELAY"
"""
.. envvar:: OTEL_BSP_SCHEDULE_DELAY

The :envvar:`OTEL_BSP_SCHEDULE_DELAY` represents the delay interval between two consecutive exports.
Default: 5000
"""

OTEL_BSP_EXPORT_TIMEOUT = "OTEL_BSP_EXPORT_TIMEOUT"
"""
.. envvar:: OTEL_BSP_EXPORT_TIMEOUT

The :envvar:`OTEL_BSP_EXPORT_TIMEOUT` represents the maximum allowed time to export data.
Default: 30000
"""

OTEL_BSP_MAX_QUEUE_SIZE = "OTEL_BSP_MAX_QUEUE_SIZE"
"""
.. envvar:: OTEL_BSP_MAX_QUEUE_SIZE

The :envvar:`OTEL_BSP_MAX_QUEUE_SIZE` represents the maximum queue size for the data export.
Default: 2048
"""

OTEL_BSP_MAX_EXPORT_BATCH_SIZE = "OTEL_BSP_MAX_EXPORT_BATCH_SIZE"
"""
.. envvar:: OTEL_BSP_MAX_EXPORT_BATCH_SIZE

The :envvar:`OTEL_BSP_MAX_EXPORT_BATCH_SIZE` represents the maximum batch size for the data export.
Default: 512
"""

OTEL_ATTRIBUTE_COUNT_LIMIT = "OTEL_ATTRIBUTE_COUNT_LIMIT"
"""
.. envvar:: OTEL_ATTRIBUTE_COUNT_LIMIT

The :envvar:`OTEL_ATTRIBUTE_COUNT_LIMIT` represents the maximum allowed attribute count for spans, events and links.
This limit is overriden by model specific limits such as OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT.
Default: 128
"""

OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT = "OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT"
"""
.. envvar:: OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT

The :envvar:`OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT` represents the maximum allowed attribute length.
"""

OTEL_EVENT_ATTRIBUTE_COUNT_LIMIT = "OTEL_EVENT_ATTRIBUTE_COUNT_LIMIT"
"""
.. envvar:: OTEL_EVENT_ATTRIBUTE_COUNT_LIMIT

The :envvar:`OTEL_EVENT_ATTRIBUTE_COUNT_LIMIT` represents the maximum allowed event attribute count.
Default: 128
"""

OTEL_LINK_ATTRIBUTE_COUNT_LIMIT = "OTEL_LINK_ATTRIBUTE_COUNT_LIMIT"
"""
.. envvar:: OTEL_LINK_ATTRIBUTE_COUNT_LIMIT

The :envvar:`OTEL_LINK_ATTRIBUTE_COUNT_LIMIT` represents the maximum allowed link attribute count.
Default: 128
"""

OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT = "OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT"
"""
.. envvar:: OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT

The :envvar:`OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT` represents the maximum allowed span attribute count.
Default: 128
"""

OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT = (
    "OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT"
)
"""
.. envvar:: OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT

The :envvar:`OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT` represents the maximum allowed length
span attribute values can have. This takes precedence over :envvar:`OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT`.
"""

OTEL_SPAN_EVENT_COUNT_LIMIT = "OTEL_SPAN_EVENT_COUNT_LIMIT"
"""
.. envvar:: OTEL_SPAN_EVENT_COUNT_LIMIT

The :envvar:`OTEL_SPAN_EVENT_COUNT_LIMIT` represents the maximum allowed span event count.
Default: 128
"""

OTEL_SPAN_LINK_COUNT_LIMIT = "OTEL_SPAN_LINK_COUNT_LIMIT"
"""
.. envvar:: OTEL_SPAN_LINK_COUNT_LIMIT

The :envvar:`OTEL_SPAN_LINK_COUNT_LIMIT` represents the maximum allowed span link count.
Default: 128
"""

OTEL_EXPORTER_JAEGER_AGENT_HOST = "OTEL_EXPORTER_JAEGER_AGENT_HOST"
"""
.. envvar:: OTEL_EXPORTER_JAEGER_AGENT_HOST

The :envvar:`OTEL_EXPORTER_JAEGER_AGENT_HOST` represents the hostname for the Jaeger agent.
Default: "localhost"
"""

OTEL_EXPORTER_JAEGER_AGENT_PORT = "OTEL_EXPORTER_JAEGER_AGENT_PORT"
"""
.. envvar:: OTEL_EXPORTER_JAEGER_AGENT_PORT

The :envvar:`OTEL_EXPORTER_JAEGER_AGENT_PORT` represents the port for the Jaeger agent.
Default: 6831
"""

OTEL_EXPORTER_JAEGER_ENDPOINT = "OTEL_EXPORTER_JAEGER_ENDPOINT"
"""
.. envvar:: OTEL_EXPORTER_JAEGER_ENDPOINT

The :envvar:`OTEL_EXPORTER_JAEGER_ENDPOINT` represents the HTTP endpoint for Jaeger traces.
Default: "http://localhost:14250"
"""

OTEL_EXPORTER_JAEGER_USER = "OTEL_EXPORTER_JAEGER_USER"
"""
.. envvar:: OTEL_EXPORTER_JAEGER_USER

The :envvar:`OTEL_EXPORTER_JAEGER_USER` represents the username to be used for HTTP basic authentication.
"""

OTEL_EXPORTER_JAEGER_PASSWORD = "OTEL_EXPORTER_JAEGER_PASSWORD"
"""
.. envvar:: OTEL_EXPORTER_JAEGER_PASSWORD

The :envvar:`OTEL_EXPORTER_JAEGER_PASSWORD` represents the password to be used for HTTP basic authentication.
"""

OTEL_EXPORTER_JAEGER_TIMEOUT = "OTEL_EXPORTER_JAEGER_TIMEOUT"
"""
.. envvar:: OTEL_EXPORTER_JAEGER_TIMEOUT

Maximum time the Jaeger exporter will wait for each batch export.
Default: 10
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

Maximum time (in seconds) the Zipkin exporter will wait for each batch export.
Default: 10
"""

OTEL_EXPORTER_OTLP_PROTOCOL = "OTEL_EXPORTER_OTLP_PROTOCOL"
"""
.. envvar:: OTEL_EXPORTER_OTLP_PROTOCOL

The :envvar:`OTEL_EXPORTER_OTLP_PROTOCOL` represents the the transport protocol for the
OTLP exporter.
"""

OTEL_EXPORTER_OTLP_CERTIFICATE = "OTEL_EXPORTER_OTLP_CERTIFICATE"
"""
.. envvar:: OTEL_EXPORTER_OTLP_CERTIFICATE

The :envvar:`OTEL_EXPORTER_OTLP_CERTIFICATE` stores the path to the certificate file for
TLS credentials of gRPC client. Should only be used for a secure connection.
"""

OTEL_EXPORTER_OTLP_HEADERS = "OTEL_EXPORTER_OTLP_HEADERS"
"""
.. envvar:: OTEL_EXPORTER_OTLP_HEADERS

The :envvar:`OTEL_EXPORTER_OTLP_HEADERS` contains the key-value pairs to be used as headers
associated with gRPC or HTTP requests.
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

The :envvar:`OTEL_EXPORTER_OTLP_TIMEOUT` is the maximum time the OTLP exporter will wait for each batch export.
Default: 10
"""

OTEL_EXPORTER_OTLP_ENDPOINT = "OTEL_EXPORTER_OTLP_ENDPOINT"
"""
.. envvar:: OTEL_EXPORTER_OTLP_ENDPOINT

The :envvar:`OTEL_EXPORTER_OTLP_ENDPOINT` target to which the exporter is going to send spans or metrics.
The endpoint MUST be a valid URL host, and MAY contain a scheme (http or https), port and path.
A scheme of https indicates a secure connection and takes precedence over the insecure configuration setting.
Default: "http://localhost:4317"
"""

OTEL_EXPORTER_OTLP_INSECURE = "OTEL_EXPORTER_OTLP_INSECURE"
"""
.. envvar:: OTEL_EXPORTER_OTLP_INSECURE

The :envvar:`OTEL_EXPORTER_OTLP_INSECURE` represents whether to enable client transport security for gRPC requests.
A scheme of https takes precedence over this configuration setting.
Default: False
"""

OTEL_EXPORTER_OTLP_TRACES_INSECURE = "OTEL_EXPORTER_OTLP_TRACES_INSECURE"
"""
.. envvar:: OTEL_EXPORTER_OTLP_TRACES_INSECURE

The :envvar:`OTEL_EXPORTER_OTLP_TRACES_INSECURE` represents whether to enable client transport security
for gRPC requests for spans. A scheme of https takes precedence over the this configuration setting.
Default: False
"""


OTEL_EXPORTER_OTLP_TRACES_ENDPOINT = "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"
"""
.. envvar:: OTEL_EXPORTER_OTLP_TRACES_ENDPOINT

The :envvar:`OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` target to which the span exporter is going to send spans.
The endpoint MUST be a valid URL host, and MAY contain a scheme (http or https), port and path.
A scheme of https indicates a secure connection and takes precedence over this configuration setting.
"""

OTEL_EXPORTER_OTLP_TRACES_PROTOCOL = "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL"
"""
.. envvar:: OTEL_EXPORTER_OTLP_TRACES_PROTOCOL

The :envvar:`OTEL_EXPORTER_OTLP_TRACES_PROTOCOL` represents the the transport protocol for spans.
"""

OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE = "OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE"
"""
.. envvar:: OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE

The :envvar:`OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE` stores the path to the certificate file for
TLS credentials of gRPC client for traces. Should only be used for a secure connection for tracing.
"""

OTEL_EXPORTER_OTLP_TRACES_HEADERS = "OTEL_EXPORTER_OTLP_TRACES_HEADERS"
"""
.. envvar:: OTEL_EXPORTER_OTLP_TRACES_HEADERS

The :envvar:`OTEL_EXPORTER_OTLP_TRACES_HEADERS` contains the key-value pairs to be used as headers for spans
associated with gRPC or HTTP requests.
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

The :envvar:`OTEL_EXPORTER_OTLP_TRACES_TIMEOUT` is the maximum time the OTLP exporter will
wait for each batch export for spans.
"""

OTEL_EXPORTER_OTLP_METRICS_INSECURE = "OTEL_EXPORTER_OTLP_METRICS_INSECURE"
"""
.. envvar:: OTEL_EXPORTER_OTLP_METRICS_INSECURE

The :envvar:`OTEL_EXPORTER_OTLP_METRICS_INSECURE` represents whether to enable client transport security
for gRPC requests for metrics. A scheme of https takes precedence over the this configuration setting.
Default: False
"""

OTEL_EXPORTER_JAEGER_CERTIFICATE = "OTEL_EXPORTER_JAEGER_CERTIFICATE"
"""
.. envvar:: OTEL_EXPORTER_JAEGER_CERTIFICATE

The :envvar:`OTEL_EXPORTER_JAEGER_CERTIFICATE` stores the path to the certificate file for
TLS credentials of gRPC client for Jaeger. Should only be used for a secure connection with Jaeger.
"""

OTEL_EXPORTER_JAEGER_AGENT_SPLIT_OVERSIZED_BATCHES = (
    "OTEL_EXPORTER_JAEGER_AGENT_SPLIT_OVERSIZED_BATCHES"
)
"""
.. envvar:: OTEL_EXPORTER_JAEGER_AGENT_SPLIT_OVERSIZED_BATCHES

The :envvar:`OTEL_EXPORTER_JAEGER_AGENT_SPLIT_OVERSIZED_BATCHES` is a boolean flag to determine whether
to split a large span batch to admire the udp packet size limit.
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

_OTEL_PYTHON_LOG_EMITTER_PROVIDER = "OTEL_PYTHON_LOG_EMITTER_PROVIDER"
"""
.. envvar:: OTEL_PYTHON_LOG_EMITTER_PROVIDER

The :envvar:`OTEL_PYTHON_LOG_EMITTER_PROVIDER` environment variable allows users to
provide the entry point for loading the log emitter provider. If not specified, SDK
LogEmitterProvider is used.
"""

OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE = (
    "OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE"
)
"""
.. envvar:: OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE

The :envvar:`OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE` environment
variable allows users to set the default aggregation temporality policy to use
on the basis of instrument kind. The valid (case-insensitive) values are:

``CUMULATIVE``: Choose ``CUMULATIVE`` aggregation temporality for all instrument kinds.
``DELTA``: Choose ``DELTA`` aggregation temporality for ``Counter``, ``Asynchronous Counter`` and ``Histogram``.
Choose ``CUMULATIVE`` aggregation temporality for ``UpDownCounter`` and ``Asynchronous UpDownCounter``.
"""
