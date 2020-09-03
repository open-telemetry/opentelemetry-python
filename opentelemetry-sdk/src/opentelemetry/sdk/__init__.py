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
The OpenTelemetry SDK package is an implementation of the OpenTelemetry
API
"""
import logging
import os

from . import metrics, trace, util

__all__ = ["metrics", "trace", "util"]

_LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if os.getenv("OTEL_LOG_LEVEL") is not None:
    key = os.getenv("OTEL_LOG_LEVEL").upper()
    if key in _LOG_LEVELS:
        logger.setLevel(_LOG_LEVELS.get(key))
    else:
        logger.warning(
            "Invalid value for environment variable OTEL_LOG_LEVEL. Defaulting to INFO."
        )
