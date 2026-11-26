# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import os

import urllib3.util.connection

from opentelemetry import metrics, trace
from opentelemetry._logs import SeverityNumber, get_logger

# The collector's certificate is issued for otel-collector.test, so connect
# that name to the collector while TLS still verifies against it.
_create_connection = urllib3.util.connection.create_connection


def _connect_to_collector(address, *args, **kwargs):
    host, port = address
    if host == "otel-collector.test":
        host = os.environ["OTEL_COLLECTOR_ENDPOINT"]
    return _create_connection((host, port), *args, **kwargs)


urllib3.util.connection.create_connection = _connect_to_collector

with trace.get_tracer(__name__).start_as_current_span("tls-span"):
    metrics.get_meter(__name__).create_counter("tls.requests").add(1)
    get_logger(__name__).emit(body="tls log", severity_number=SeverityNumber.INFO)
