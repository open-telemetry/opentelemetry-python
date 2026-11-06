# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""The outcome recorded on a finished span.

A span carries a :class:`Status` saying whether the operation it covers
succeeded. The status is :attr:`StatusCode.UNSET` unless instrumentation sets
it, and a non-empty description may accompany it only when the code is
:attr:`StatusCode.ERROR`. A description that is ``None`` or the empty string
is stored whatever the code is.
"""

import enum
import logging

logger = logging.getLogger(__name__)


class StatusCode(enum.Enum):
    """Represents the canonical set of status codes of a finished Span."""

    UNSET = 0
    """The default status."""

    OK = 1
    """The operation has been validated by an Application developer or Operator to have completed successfully."""

    ERROR = 2
    """The operation contains an error."""


class Status:
    """Represents the status of a finished Span.

    Args:
        status_code: The canonical status code that describes the result
            status of the operation.
        description: An optional description of the status.

    A non-empty description is kept only when ``status_code`` is
    :attr:`StatusCode.ERROR` and the description is a :class:`str`. Otherwise
    it is discarded and a warning is logged, which is what the specification
    requires. A description that is ``None`` or the empty string skips those
    checks altogether and is stored as it was given, with no warning.
    """

    def __init__(
        self,
        status_code: StatusCode = StatusCode.UNSET,
        description: str | None = None,
    ):
        """Build the status, discarding a description that is not permitted.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._status_code = status_code
        self._description = None

        if description:
            if not isinstance(description, str):
                logger.warning("Invalid status description type, expected str")
                return
            if status_code is not StatusCode.ERROR:
                logger.warning("description should only be set when status_code is set to StatusCode.ERROR")
                return

        self._description = description

    @property
    def status_code(self) -> StatusCode:
        """Represents the canonical status code of a finished Span.

        Returns:
            The code this status was built with.
        """
        return self._status_code

    @property
    def description(self) -> str | None:
        """Status description.

        Returns:
            The description as it was stored. That is ``None`` when none was
            supplied and when the one supplied was discarded for not being a
            :class:`str` or for accompanying a non-error status code, and the
            empty string when the empty string was supplied.
        """
        return self._description

    @property
    def is_ok(self) -> bool:
        """Returns false if this represents an error, true otherwise.

        Returns:
            ``True`` when the status code is :attr:`StatusCode.OK` or
            :attr:`StatusCode.UNSET`, ``False`` when it is
            :attr:`StatusCode.ERROR`.
        """
        return self.is_unset or self._status_code is StatusCode.OK

    @property
    def is_unset(self) -> bool:
        """Returns true if unset, false otherwise.

        Returns:
            ``True`` when no status code has been set on this status, which is
            the state of a span that finished without instrumentation deciding
            its outcome.
        """
        return self._status_code is StatusCode.UNSET
