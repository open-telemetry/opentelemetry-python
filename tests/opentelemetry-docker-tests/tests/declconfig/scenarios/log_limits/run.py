# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry._logs import get_logger

# Once the count limit is reached, new attributes are dropped.
get_logger(__name__).emit(body="limited log", attributes={"a": "abcdefgh", "b": 1, "dropped": 0})
