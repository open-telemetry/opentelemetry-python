# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry import trace
from opentelemetry._logs import SeverityNumber, get_logger

logger = get_logger(__name__)

with trace.get_tracer(__name__).start_as_current_span("handler"):
    logger.emit(
        body="user logged in",
        severity_number=SeverityNumber.WARN,
        severity_text="WARN",
        event_name="user.login",
        attributes={"user.id": "u-1"},
    )
logger.emit(body={"kind": "structured", "count": 2}, severity_number=SeverityNumber.INFO)
