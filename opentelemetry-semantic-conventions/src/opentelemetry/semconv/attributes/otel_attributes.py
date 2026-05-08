# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from enum import Enum
from typing import Final

OTEL_SCOPE_NAME: Final = "otel.scope.name"
"""
The name of the instrumentation scope - (`InstrumentationScope.Name` in OTLP).
"""

OTEL_SCOPE_VERSION: Final = "otel.scope.version"
"""
The version of the instrumentation scope - (`InstrumentationScope.Version` in OTLP).
"""

OTEL_STATUS_CODE: Final = "otel.status_code"
"""
Name of the code, either "OK" or "ERROR". MUST NOT be set if the status code is UNSET.
"""

OTEL_STATUS_DESCRIPTION: Final = "otel.status_description"
"""
Description of the Status if it has a value, otherwise not set.
"""


class OtelStatusCodeValues(Enum):
    OK = "OK"
    """The operation has been validated by an Application developer or Operator to have completed successfully."""
    ERROR = "ERROR"
    """The operation contains an error."""
