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
The OpenTelemetry SDK package is an implementation of the OpenTelemetry API.
"""

import logging
from os import environ

from opentelemetry.sdk.environment_variables import OTEL_LOG_LEVEL

# "warn" is accepted alongside "warning" because OTel canonical short names
# use "WARN", so users following OTel documentation will naturally try "warn".
_OTEL_LOG_LEVEL_TO_PYTHON = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARNING,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

_otel_log_level_raw = environ.get(OTEL_LOG_LEVEL)
if _otel_log_level_raw:
    _logger = logging.getLogger(__name__)
    _otel_log_level = _otel_log_level_raw.lower()
    if _otel_log_level in _OTEL_LOG_LEVEL_TO_PYTHON:
        _logger.setLevel(_OTEL_LOG_LEVEL_TO_PYTHON[_otel_log_level])
    else:
        _logger.warning(
            "Invalid value for OTEL_LOG_LEVEL: %r. "
            "Valid values: debug, info, warn, warning, error, critical. "
            "Logger level unchanged.",
            _otel_log_level_raw,
        )
