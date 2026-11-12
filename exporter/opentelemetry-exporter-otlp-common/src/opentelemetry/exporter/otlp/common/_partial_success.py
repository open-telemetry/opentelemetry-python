# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from logging import Logger

_WARNING_FORMAT: Final[str] = "OTLP partial success exporting %s to %s (rejected=%d): %s"


def _report_partial_success(
    logger: Logger,
    signal: str,
    endpoint: str,
    rejected: int,
    error_message: str,
) -> int:
    """Warn about the partial success an OTLP export response reports.

    :param logger: The logger the warning is sent to.
    :param signal: The signal being exported, as the caller names it.
    :param endpoint: The endpoint the export was sent to.
    :param rejected: The rejected count the server reported.
    :param error_message: The error message the server reported, empty when it
        reported none.
    :returns: The number of rejected items, which is zero when the server
        reported a negative count.
    """
    try:
        rejected = max(rejected, 0)
        if not rejected and not error_message:
            return 0

        logger.warning(_WARNING_FORMAT, signal, endpoint, rejected, error_message)
        return rejected
    # pylint: disable-next=broad-exception-caught
    except Exception:
        return 0
