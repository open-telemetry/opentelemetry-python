# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry.exporter.otlp.proto.http import Compression, _OTLP_HTTP_HEADERS
from opentelemetry.exporter.otlp.proto.http.version import __version__


def test_compression_no_compression_value():
    assert Compression.NoCompression.value == "none"


def test_compression_deflate_value():
    assert Compression.Deflate.value == "deflate"


def test_compression_gzip_value():
    assert Compression.Gzip.value == "gzip"


def test_otlp_http_headers_content_type():
    assert _OTLP_HTTP_HEADERS["Content-Type"] == "application/x-protobuf"


def test_otlp_http_headers_user_agent():
    assert _OTLP_HTTP_HEADERS["User-Agent"] == f"OTel-OTLP-Exporter-Python/{__version__}"
