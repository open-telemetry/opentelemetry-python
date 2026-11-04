# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry._logs import get_logger

get_logger("enabled.lib").emit(body="enabled log")
get_logger("disabled.lib").emit(body="disabled log")
