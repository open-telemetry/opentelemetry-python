# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry._logs import get_logger

get_logger(__name__).emit(body="grpc log")
