# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
"""Turning an exception attached to a log record into attributes.

``LogRecord`` carries an ``exception`` field holding a live ``BaseException``.
Nothing downstream can serialise that, so before a record reaches a processor
the SDK derives the three ``exception.*`` semantic convention attributes from
it. The helpers here do that derivation in the three shapes ``Logger.emit``
needs: build a fresh record, copy an existing one, or edit one in place.

An attribute the caller set by hand always wins over the derived value, in
every one of those shapes.
"""

from __future__ import annotations

import traceback

from opentelemetry._logs import LogRecord
from opentelemetry.attributes import BoundedAttributes
from opentelemetry.semconv.attributes import exception_attributes
from opentelemetry.util.types import AnyValue, Attributes


def _get_exception_attributes(
    exception: BaseException,
) -> dict[str, AnyValue]:
    """Derive the three ``exception.*`` attributes from an exception.

    The type is qualified with the defining module, so a ``ValueError`` comes
    out as ``ValueError`` while a custom class comes out as
    ``mypackage.mymodule.MyError``. Builtins are left unqualified.

    Args:
        exception: The exception to describe. Its ``__traceback__`` supplies
            the stack trace, and an exception that was never raised has none,
            which yields a one-line trace holding only the exception itself.

    Returns:
        A mapping with ``exception.type``, ``exception.message`` and
        ``exception.stacktrace``. The message is ``str(exception)``, which is
        the empty string for an exception constructed with no arguments. All
        three keys are always present.
    """
    stacktrace = "".join(traceback.format_exception(type(exception), value=exception, tb=exception.__traceback__))
    module = type(exception).__module__
    qualname = type(exception).__qualname__
    exception_type = f"{module}.{qualname}" if module and module != "builtins" else qualname
    return {
        exception_attributes.EXCEPTION_TYPE: exception_type,
        exception_attributes.EXCEPTION_MESSAGE: str(exception),
        exception_attributes.EXCEPTION_STACKTRACE: stacktrace,
    }


def _get_attributes_with_exception(
    attributes: Attributes,
    exception: BaseException | None,
) -> Attributes:
    """Merge the derived exception attributes under the caller's attributes.

    A key the caller already set is never overwritten, so passing
    ``exception.message`` explicitly keeps that text and discards the one
    derived from the exception.

    Args:
        attributes: The attributes already on the record. ``None`` is treated
            as an empty mapping.
        exception: The exception to describe, or ``None`` to leave
            ``attributes`` untouched.

    Returns:
        ``attributes`` itself, unchanged and possibly ``None``, when
        ``exception`` is ``None``. A new ``BoundedAttributes`` carrying the
        same ``maxlen`` and ``max_value_len`` when ``attributes`` was one,
        which means the exception attributes are themselves subject to those
        limits and can be dropped or truncated. Its ``dropped`` count starts
        from the input's and is then raised by however many of the three
        exception attributes the count limit refused, so it is at least the
        input's count rather than equal to it. A plain ``dict`` otherwise.
        The input mapping is never modified.
    """
    if exception is None:
        return attributes

    exception_attributes_map = _get_exception_attributes(exception)
    if attributes is None:
        attributes_map: Attributes = {}
    else:
        attributes_map = attributes

    if isinstance(attributes_map, BoundedAttributes):
        bounded_attributes = attributes_map
        merged = BoundedAttributes(
            maxlen=bounded_attributes.maxlen,
            attributes=bounded_attributes,
            immutable=False,
            max_value_len=bounded_attributes.max_value_len,
        )
        merged.dropped = bounded_attributes.dropped
        for key, value in exception_attributes_map.items():
            if key not in merged:
                merged[key] = value
        return merged

    return exception_attributes_map | dict(attributes_map.items())


def _copy_log_record(
    record: LogRecord,
    attributes: Attributes,
) -> LogRecord:
    """Shallow-copy a log record, swapping in a different attribute mapping.

    Every other field is carried over by reference. ``trace_id``, ``span_id``
    and ``trace_flags`` are reassigned after construction because the
    ``LogRecord`` constructor otherwise re-derives them from ``context``, which
    would lose the values a caller set by hand.

    Args:
        record: The record to copy. It is not modified.
        attributes: The attribute mapping the copy gets. Passing the mapping of
            ``record`` makes the two records share it.

    Returns:
        The new record.
    """
    copied_record = LogRecord(
        timestamp=record.timestamp,
        observed_timestamp=record.observed_timestamp,
        context=record.context,
        severity_text=record.severity_text,
        severity_number=record.severity_number,
        body=record.body,
        attributes=attributes,
        event_name=record.event_name,
        exception=getattr(record, "exception", None),
    )
    copied_record.trace_id = record.trace_id
    copied_record.span_id = record.span_id
    copied_record.trace_flags = record.trace_flags
    return copied_record


def _copy_log_record_with_exception(record: LogRecord) -> LogRecord:
    """Copy a log record with its exception rendered into attributes.

    ``Logger.emit`` uses this when the caller hands it a record it does not
    own, so that the caller's record keeps the attribute mapping it had.

    Args:
        record: The record to copy. It is not modified, including its
            attributes.

    Returns:
        A new record whose attributes carry ``exception.type``,
        ``exception.message`` and ``exception.stacktrace``. When
        ``record.exception`` is ``None`` the copy shares the original attribute
        mapping rather than getting one of its own.
    """
    return _copy_log_record(
        record,
        _get_attributes_with_exception(record.attributes, record.exception),
    )


def _set_log_record_exception_attributes(record: LogRecord) -> None:
    """Render a log record's exception into its attributes, in place.

    ``Logger.emit`` uses this on a ``ReadWriteLogRecord``, which the SDK built
    itself and is free to edit. The attribute mapping is replaced rather than
    added to, so a ``BoundedAttributes`` mapping is swapped for a new one that
    inherits its limits and its dropped count.

    Args:
        record: The record to edit. Nothing happens when its ``exception`` is
            ``None``.
    """
    record.attributes = _get_attributes_with_exception(
        record.attributes,
        record.exception,
    )


def _create_log_record_with_exception(
    *,
    timestamp: int | None = None,
    observed_timestamp: int | None = None,
    context=None,
    severity_number=None,
    severity_text: str | None = None,
    body: AnyValue | None = None,
    attributes: Attributes = None,
    event_name: str | None = None,
    exception: BaseException | None = None,
) -> LogRecord:
    """Build a log record from loose arguments, folding in an exception.

    ``Logger.emit`` uses this on the path where the caller passed individual
    keyword arguments instead of a ready-made record.

    Args:
        timestamp: When the event happened, in nanoseconds since the Unix
            epoch. ``None`` leaves the field unset, and a consumer is then
            expected to fall back to ``observed_timestamp``.
        observed_timestamp: When the SDK saw the event, in nanoseconds since
            the Unix epoch. ``None`` makes ``LogRecord`` fill it with the
            current time.
        context: The context to take the trace id, span id and trace flags
            from. ``None`` makes ``LogRecord`` use the current context.
        severity_number: The severity as an ``opentelemetry._logs``
            ``SeverityNumber``, or ``None`` to leave it unset.
        severity_text: The original severity label of the logging system the
            record came from, or ``None``.
        body: The payload of the event. Any attribute value type is accepted,
            including a mapping or a sequence.
        attributes: Attributes to attach. A key given here survives even when
            the derived exception attributes use the same key.
        event_name: The name identifying the class of event, or ``None`` for an
            unnamed log record.
        exception: The exception to describe in ``exception.*`` attributes. It
            is also stored on the returned record, so the field still holds the
            live exception object afterwards.

    Returns:
        The new record.
    """
    return LogRecord(
        timestamp=timestamp,
        observed_timestamp=observed_timestamp,
        context=context,
        severity_number=severity_number,
        severity_text=severity_text,
        body=body,
        attributes=_get_attributes_with_exception(attributes, exception),
        event_name=event_name,
        exception=exception,
    )
