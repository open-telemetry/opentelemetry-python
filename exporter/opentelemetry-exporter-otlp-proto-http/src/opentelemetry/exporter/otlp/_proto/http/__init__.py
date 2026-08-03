# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from enum import Enum

from .version import __version__

_OTLP_HTTP_HEADERS = {
    "Content-Type": "application/x-protobuf",
    "User-Agent": "OTel-OTLP-Exporter-Python/" + __version__,
}


class Compression(Enum):
    NoCompression = "none"
    Deflate = "deflate"
    Gzip = "gzip"
