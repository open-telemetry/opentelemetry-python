# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from logging import getLogger

from opentelemetry.sdk.error_handler import ErrorHandler

logger = getLogger(__name__)


# pylint: disable=too-many-ancestors
class ErrorHandler1(ErrorHandler, IndexError, KeyError):
    def _handle(self, error: Exception, *args, **kwargs):
        if isinstance(error, IndexError):
            logger.exception("ErrorHandler1 handling an IndexError")

        elif isinstance(error, KeyError):
            logger.exception("ErrorHandler1 handling a KeyError")
