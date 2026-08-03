# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from .version import __version__

_USER_AGENT_HEADER_VALUE = "OTel-OTLP-Exporter-Python/" + __version__
_OTLP_GRPC_CHANNEL_OPTIONS = [
    ("grpc.primary_user_agent", _USER_AGENT_HEADER_VALUE)
]
