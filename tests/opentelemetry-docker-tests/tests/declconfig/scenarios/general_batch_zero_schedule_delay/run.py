# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import trace
from opentelemetry._logs import SeverityNumber, get_logger

tracer = trace.get_tracer(__name__)
logger = get_logger(__name__)

for _ in range(5):
    with tracer.start_as_current_span("zero-delay-span"):
        pass

with tracer.start_as_current_span("handler"):
    logger.emit(body="zero delay log", severity_number=SeverityNumber.INFO)
