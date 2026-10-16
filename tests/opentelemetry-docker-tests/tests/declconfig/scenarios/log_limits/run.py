# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry._logs import get_logger

# Once the count limit is reached, the oldest attribute is dropped.
get_logger(__name__).emit(body="limited log", attributes={"dropped": 0, "a": "abcdefgh", "b": 1})
