# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

from google.protobuf.message import DecodeError

if TYPE_CHECKING:
    from logging import Logger

    from google.protobuf.message import Message

_REJECTED_FIELDS: Final[tuple[str, ...]] = (
    "rejected_spans",
    "rejected_data_points",
    "rejected_log_records",
    "rejected_profiles",
)


def _warning_format(signal: str) -> str:
    """Build the format string a partial success warning is logged with.

    :param signal: The signal being exported, as the caller names it.
    :returns: A format string taking the endpoint and the detail as arguments.

    The ``DuplicateFilter`` installed on the gRPC exporter logger and on the
    OTLP/HTTP log exporter logger keys on ``LogRecord.msg``, so the signal goes
    in the string and the endpoint and the detail stay out: repeats of one
    signal collapse, and the three gRPC signals, which share one logger, do not
    collapse into each other.
    """
    return f"OTLP partial success exporting {signal} to %s: %s"


def _partial_success_detail(response: Message | None) -> str | None:
    """Describe the partial success an OTLP export response reports.

    :param response: A parsed ``Export<signal>ServiceResponse`` message, or
        ``None``.
    :returns: A description of the rejected items and the error message the
        server sent, to be logged as the last argument of the format string
        ``_warning_format`` builds, or ``None`` when there is nothing to report.

    The OTLP specification treats a ``partial_success`` field holding a zero
    rejected count and an empty error message as equivalent to the field being
    absent, so both cases return ``None``. A ``response`` of ``None`` returns
    ``None`` too, because a gRPC stub is free to return nothing and reporting
    is not worth failing an export the server accepted.

    A message whose type does not define ``partial_success`` at all returns
    ``None`` as well. ``HasField`` raises ``ValueError`` for a field the type
    does not define, and ``OTLPExporterMixin`` is public, so a subclass may
    export through a service of its own whose response carries no such field.
    """
    if response is None or "partial_success" not in response.DESCRIPTOR.fields_by_name:
        return None

    if not response.HasField("partial_success"):
        return None

    message: Any = response
    partial_success = message.partial_success
    rejected = 0
    rejected_field = ""
    for field_name in _REJECTED_FIELDS:
        if hasattr(partial_success, field_name):
            rejected = getattr(partial_success, field_name)
            rejected_field = field_name
            break

    error_message = partial_success.error_message
    if not rejected and not error_message:
        return None

    if not rejected:
        return error_message

    kind = rejected_field.removeprefix("rejected_").replace("_", " ")
    if rejected == 1:
        kind = kind.removesuffix("s")
    if not error_message:
        return f"the server rejected {rejected} {kind}"
    return f"the server rejected {rejected} {kind}: {error_message}"


def _log_partial_success(
    serialized_response: bytes,
    response_type: type[Message],
    logger: Logger,
    signal: str,
    endpoint: str,
) -> None:
    """Log the partial success reported by a serialized OTLP export response.

    :param serialized_response: The raw response body returned by the server.
    :param response_type: The ``Export<signal>ServiceResponse`` class to parse
        ``serialized_response`` with.
    :param logger: The logger that receives the warning.
    :param signal: The signal being exported, named as the surrounding failure
        messages name it, so a process running several exporters can tell which
        one is dropping data.
    :param endpoint: The endpoint the export was sent to, for the same reason.

    A response that cannot be parsed is logged at debug level and otherwise
    ignored, so that a malformed body never turns a successful export into a
    failed one. Debug rather than warning, because the server accepted the
    request and a body the exporter cannot read tells the user nothing they can
    act on. Any status from 200 to 399 counts as a successful export, so an
    unparsable body is what a redirect page or a proxy error page looks like
    here, and warning on those would fire once per export.

    The pure-Python protobuf runtime raises ``UnicodeDecodeError`` for a string
    field holding invalid UTF-8, where the default runtime raises
    ``DecodeError``, so both are caught.
    """
    if not serialized_response:
        return

    response = response_type()
    try:
        response.ParseFromString(serialized_response)
    except (DecodeError, UnicodeDecodeError) as error:
        logger.debug("Failed to parse the OTLP export response: %s", error)
        return

    detail = _partial_success_detail(response)
    if detail is not None:
        logger.warning(_warning_format(signal), endpoint, detail)
