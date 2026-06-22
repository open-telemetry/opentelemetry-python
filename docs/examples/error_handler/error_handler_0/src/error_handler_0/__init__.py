# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from logging import getLogger

from opentelemetry.sdk.error_handler import ErrorHandler

logger = getLogger(__name__)


class ErrorHandler0(ErrorHandler, ZeroDivisionError):
    def _handle(self, error: Exception, *args, **kwargs):
        logger.exception("ErrorHandler0 handling a ZeroDivisionError")
