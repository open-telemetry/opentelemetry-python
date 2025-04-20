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
This library allows to export tracing data to an OTLP collector using JSON over HTTP.

Usage
-----

The **OTLP JSON HTTP Exporter** allows to export `OpenTelemetry`_ traces, metrics, and logs to the
`OTLP`_ collector, using JSON encoding over HTTP.

You can configure the exporter with the following environment variables:

- :envvar:`OTEL_EXPORTER_OTLP_TRACES_TIMEOUT`
- :envvar:`OTEL_EXPORTER_OTLP_TRACES_PROTOCOL`
- :envvar:`OTEL_EXPORTER_OTLP_TRACES_HEADERS`
- :envvar:`OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`
- :envvar:`OTEL_EXPORTER_OTLP_TRACES_COMPRESSION`
- :envvar:`OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE`
- :envvar:`OTEL_EXPORTER_OTLP_TIMEOUT`
- :envvar:`OTEL_EXPORTER_OTLP_PROTOCOL`
- :envvar:`OTEL_EXPORTER_OTLP_HEADERS`
- :envvar:`OTEL_EXPORTER_OTLP_ENDPOINT`
- :envvar:`OTEL_EXPORTER_OTLP_COMPRESSION`
- :envvar:`OTEL_EXPORTER_OTLP_CERTIFICATE`

.. _OTLP: https://github.com/open-telemetry/opentelemetry-collector/
.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/
"""

import enum

from .version import __version__

_OTLP_JSON_HTTP_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "OTel-OTLP-Exporter-Python/" + __version__,
}


# pylint: disable=invalid-name
class Compression(enum.Enum):
    NoCompression = "none"
    Deflate = "deflate"
    Gzip = "gzip"
