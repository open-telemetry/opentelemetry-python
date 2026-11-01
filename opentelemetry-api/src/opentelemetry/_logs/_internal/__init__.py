# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
"""
The OpenTelemetry logging API describes the classes used to generate logs and events.

The :class:`.LoggerProvider` provides users access to the :class:`.Logger`.

This module provides abstract (i.e. unimplemented) classes required for
logging, and a concrete no-op implementation :class:`.NoOpLogger` that allows applications
to use the API package alone without a supporting implementation.

To get a logger, you need to provide the package name from which you are
calling the logging APIs to OpenTelemetry by calling `LoggerProvider.get_logger`
with the calling module name and the version of your package.

The following code shows how to obtain a logger using the global :class:`.LoggerProvider`::

    from opentelemetry._logs import get_logger

    logger = get_logger("example-logger")

.. versionadded:: 1.15.0
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from logging import getLogger
from os import environ
from time import time_ns
from typing import cast, overload

from typing_extensions import deprecated

from opentelemetry._logs.severity import SeverityNumber
from opentelemetry.context import get_current
from opentelemetry.context.context import Context
from opentelemetry.environment_variables import _OTEL_PYTHON_LOGGER_PROVIDER
from opentelemetry.trace import get_current_span
from opentelemetry.trace.span import TraceFlags
from opentelemetry.util._once import Once
from opentelemetry.util._providers import _load_provider
from opentelemetry.util.types import AnyValue, Attributes

_logger = getLogger(__name__)


class LogRecord(ABC):
    """A LogRecord instance represents an event being logged.

    LogRecord instances are created and emitted via `Logger`
    every time something is logged. They contain all the information
    pertinent to the event being logged.

    Args:
        timestamp: When the event occurred, as nanoseconds since the Unix
            epoch.
        observed_timestamp: When the event was observed by the collection
            system, as nanoseconds since the Unix epoch. Defaults to the time
            the record is built, whether or not ``timestamp`` was given.
        context: The context the record belongs to. Defaults to the current
            context, from which the trace id, span id and trace flags are
            taken.
        trace_id: The id of the trace the record belongs to. Defaults to the
            one in ``context``.
        span_id: The id of the span the record belongs to. Defaults to the one
            in ``context``.
        trace_flags: The sampling flags of the span the record belongs to.
            Defaults to the ones in ``context``.
        severity_text: The severity as the originating system spelled it, for
            example ``"WARN"``.
        severity_number: The severity on the OpenTelemetry scale.
        body: The payload of the event.
        attributes: Further name/value pairs describing the event.
        event_name: The name identifying the class of event.
        exception: An exception to record alongside the event.

    .. deprecated:: 1.35.0
        Passing ``trace_id``, ``span_id`` or ``trace_flags`` is deprecated.
        Pass ``context`` instead.
    """

    __slots__ = (
        "timestamp",
        "observed_timestamp",
        "context",
        "trace_id",
        "span_id",
        "trace_flags",
        "severity_text",
        "severity_number",
        "body",
        "attributes",
        "event_name",
        "exception",
    )

    @overload
    def __init__(
        self,
        *,
        timestamp: int | None = None,
        observed_timestamp: int | None = None,
        context: Context | None = None,
        severity_text: str | None = None,
        severity_number: SeverityNumber | None = None,
        body: AnyValue = None,
        attributes: Attributes = None,
        event_name: str | None = None,
        exception: BaseException | None = None,
    ) -> None: ...

    @overload
    @deprecated(
        "LogRecord init with `trace_id`, `span_id`, and/or `trace_flags` is deprecated since 1.35.0. Use `context` instead."
    )
    def __init__(
        self,
        *,
        timestamp: int | None = None,
        observed_timestamp: int | None = None,
        trace_id: int | None = None,
        span_id: int | None = None,
        trace_flags: TraceFlags | None = None,
        severity_text: str | None = None,
        severity_number: SeverityNumber | None = None,
        body: AnyValue = None,
        attributes: Attributes = None,
    ) -> None: ...

    def __init__(
        self,
        *,
        timestamp: int | None = None,
        observed_timestamp: int | None = None,
        context: Context | None = None,
        trace_id: int | None = None,
        span_id: int | None = None,
        trace_flags: TraceFlags | None = None,
        severity_text: str | None = None,
        severity_number: SeverityNumber | None = None,
        body: AnyValue = None,
        attributes: Attributes = None,
        event_name: str | None = None,
        exception: BaseException | None = None,
    ) -> None:
        """Build the record, filling in the timestamps and trace fields.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        if not context:
            context = get_current()
        span_context = get_current_span(context).get_span_context()
        self.timestamp = timestamp
        if observed_timestamp is None:
            observed_timestamp = time_ns()
        self.observed_timestamp = observed_timestamp
        self.context = context
        self.trace_id = trace_id or span_context.trace_id
        self.span_id = span_id or span_context.span_id
        self.trace_flags = trace_flags or span_context.trace_flags
        self.severity_text = severity_text
        self.severity_number = severity_number
        self.body = body
        self.attributes = attributes
        self.event_name = event_name
        self.exception = exception


class Logger(ABC):
    """Handles emitting events and logs via `LogRecord`.

    A logger is bound to one instrumentation scope, named by the arguments it
    is built with. Obtain one from :meth:`LoggerProvider.get_logger` rather
    than constructing it directly.

    Args:
        name: The name of the instrumenting module, package or class, not the
            name of the thing being instrumented.
        version: The version string of the instrumenting library.
        schema_url: The Schema URL of the emitted telemetry.
        attributes: The instrumentation scope attributes to associate with
            emitted telemetry.
    """

    def __init__(
        self,
        name: str,
        version: str | None = None,
        schema_url: str | None = None,
        attributes: Attributes = None,
    ) -> None:
        """Record the instrumentation scope this logger is bound to.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        super().__init__()
        self._name = name
        self._version = version
        self._schema_url = schema_url
        self._attributes = attributes

    @overload
    def emit(
        self,
        *,
        timestamp: int | None = None,
        observed_timestamp: int | None = None,
        context: Context | None = None,
        severity_number: SeverityNumber | None = None,
        severity_text: str | None = None,
        body: AnyValue | None = None,
        attributes: Attributes = None,
        event_name: str | None = None,
        exception: BaseException | None = None,
    ) -> None: ...

    @overload
    def emit(
        self,
        record: LogRecord,
    ) -> None: ...

    @abstractmethod
    def emit(
        self,
        record: LogRecord | None = None,
        *,
        timestamp: int | None = None,
        observed_timestamp: int | None = None,
        context: Context | None = None,
        severity_number: SeverityNumber | None = None,
        severity_text: str | None = None,
        body: AnyValue | None = None,
        attributes: Attributes = None,
        event_name: str | None = None,
        exception: BaseException | None = None,
    ) -> None:
        """Emits a :class:`LogRecord` representing a log to the processing pipeline.

        The record is supplied either as a built :class:`LogRecord` positional
        argument or as the keyword arguments to build one from, never both.

        Args:
            record: A fully built :class:`LogRecord` to emit. When it is
                given, every keyword argument below is ignored. When it is
                ``None``, a record is built from the keyword arguments.
            timestamp: When the event occurred, as nanoseconds since the Unix
                epoch. Left unset when omitted, so the record carries ``None``
                rather than a time the API invented.
            observed_timestamp: When the event was observed by the collection
                system, as nanoseconds since the Unix epoch. Defaults to the
                time the record is built.
            context: The context the record belongs to, used to associate it
                with the active span. Defaults to the current context.
            severity_number: The severity of the event on the OpenTelemetry
                scale.
            severity_text: The severity of the event as the originating system
                spelled it, for example ``"WARN"``.
            body: The payload of the event. A string for an ordinary log line,
                or any other ``AnyValue`` for
                structured content.
            attributes: Further name/value pairs describing the event.
            event_name: The name identifying the class of event, for a
                structured event rather than a free-form log line.
            exception: An exception to record alongside the event. Its type,
                message and stack trace are attached to the record.
        """

    @abstractmethod
    def enabled(
        self,
        *,
        context: Context | None = None,
        severity_number: SeverityNumber | None = None,
        event_name: str | None = None,
    ) -> bool:
        """Returns whether the logger is enabled for the given arguments.

        Instrumentation should call this before performing expensive work to
        construct a log record, and skip that work if ``False`` is returned.

        The returned value may change over time and should be checked each time
        before emitting a log record.

        Args:
            context: The context the record would belong to. Defaults to the
                current context.
            severity_number: The severity the record would carry.
            event_name: The name of the event the record would carry.

        Returns:
            ``True`` when a record emitted with these arguments would be
            processed, ``False`` when it would be discarded.
        """


class NoOpLogger(Logger):
    """The default Logger used when no Logger implementation is available.

    All operations are no-op.
    """

    @overload
    def emit(
        self,
        *,
        timestamp: int | None = None,
        observed_timestamp: int | None = None,
        context: Context | None = None,
        severity_number: SeverityNumber | None = None,
        severity_text: str | None = None,
        body: AnyValue | None = None,
        attributes: Attributes = None,
        event_name: str | None = None,
        exception: BaseException | None = None,
    ) -> None: ...

    @overload
    def emit(  # pylint:disable=arguments-differ
        self,
        record: LogRecord,
    ) -> None: ...

    def emit(
        self,
        record: LogRecord | None = None,
        *,
        timestamp: int | None = None,
        observed_timestamp: int | None = None,
        context: Context | None = None,
        severity_number: SeverityNumber | None = None,
        severity_text: str | None = None,
        body: AnyValue | None = None,
        attributes: Attributes = None,
        event_name: str | None = None,
        exception: BaseException | None = None,
    ) -> None:
        """Discard the call, since this logger builds no record at all.

        Nothing here is read. No :class:`LogRecord` is built from the keyword
        arguments, so no timestamp is taken and no context is consulted.

        Args:
            record: Ignored.
            timestamp: Ignored.
            observed_timestamp: Ignored.
            context: Ignored.
            severity_number: Ignored.
            severity_text: Ignored.
            body: Ignored.
            attributes: Ignored.
            event_name: Ignored.
            exception: Ignored.
        """

    def enabled(
        self,
        *,
        context: Context | None = None,
        severity_number: SeverityNumber | None = None,
        event_name: str | None = None,
    ) -> bool:
        """Report that nothing is ever emitted.

        The body is ``return False`` and reads no argument, so none of the
        three is consulted and no context lookup happens.

        Args:
            context: Ignored.
            severity_number: Ignored.
            event_name: Ignored.

        Returns:
            Always ``False``, so instrumentation skips building a record it
            would only discard.
        """
        return False


class ProxyLogger(Logger):
    """A logger that stands in until a real provider is set globally.

    Every record emitted through it is discarded while no
    :class:`LoggerProvider` has been installed. Once one is, the proxy
    resolves a real logger for its instrumentation scope, caches it, and
    forwards everything from then on.

    Args:
        name: The name of the instrumenting module, passed on to
            :meth:`LoggerProvider.get_logger`.
        version: The version of the instrumenting module.
        schema_url: The schema URL the emitted records follow.
        attributes: Attributes describing the instrumentation scope.
    """

    def __init__(  # pylint: disable=super-init-not-called
        self,
        name: str,
        version: str | None = None,
        schema_url: str | None = None,
        attributes: Attributes = None,
    ):
        """Record what to ask the global provider for once it exists.

        Every parameter is documented on the class itself, since that is the
        form the API reference renders.
        """
        self._name = name
        self._version = version
        self._schema_url = schema_url
        self._attributes = attributes
        self._real_logger: Logger | None = None
        self._noop_logger = NoOpLogger(name)

    @property
    def _logger(self) -> Logger:
        """Return the logger to delegate to, resolving it on first use.

        Returns:
            The logger obtained from the global :class:`LoggerProvider` once
            one is set, cached thereafter. A :class:`NoOpLogger` until then,
            built once and returned on every call, which the proxy never
            adopts as its real logger, so a later provider is still picked up.
        """
        if self._real_logger:
            return self._real_logger

        if _LOGGER_PROVIDER:
            self._real_logger = _LOGGER_PROVIDER.get_logger(
                self._name,
                self._version,
                self._schema_url,
                self._attributes,
            )
            return self._real_logger
        return self._noop_logger

    @overload
    def emit(
        self,
        *,
        timestamp: int | None = None,
        observed_timestamp: int | None = None,
        context: Context | None = None,
        severity_number: SeverityNumber | None = None,
        severity_text: str | None = None,
        body: AnyValue | None = None,
        attributes: Attributes = None,
        event_name: str | None = None,
        exception: BaseException | None = None,
    ) -> None: ...

    @overload
    def emit(  # pylint:disable=arguments-differ
        self,
        record: LogRecord,
    ) -> None: ...

    def emit(
        self,
        record: LogRecord | None = None,
        *,
        timestamp: int | None = None,
        observed_timestamp: int | None = None,
        context: Context | None = None,
        severity_number: SeverityNumber | None = None,
        severity_text: str | None = None,
        body: AnyValue | None = None,
        attributes: Attributes = None,
        event_name: str | None = None,
        exception: BaseException | None = None,
    ) -> None:
        """Forward the log record to the real logger once one is available.

        Until a :class:`LoggerProvider` is set globally, the record is handed
        to a :class:`NoOpLogger` and discarded.

        Args:
            record: A fully built :class:`LogRecord` to emit. When it is
                given, every keyword argument below is ignored. When it is
                ``None``, a record is built from the keyword arguments.
            timestamp: When the event occurred, as nanoseconds since the Unix
                epoch. Left unset when omitted, so the record carries ``None``
                rather than a time the API invented.
            observed_timestamp: When the event was observed by the collection
                system, as nanoseconds since the Unix epoch. Defaults to the
                time the record is built.
            context: The context the record belongs to, used to associate it
                with the active span. Defaults to the current context.
            severity_number: The severity of the event on the OpenTelemetry
                scale.
            severity_text: The severity of the event as the originating system
                spelled it, for example ``"WARN"``.
            body: The payload of the event. A string for an ordinary log line,
                or any other ``AnyValue`` for
                structured content.
            attributes: Further name/value pairs describing the event.
            event_name: The name identifying the class of event, for a
                structured event rather than a free-form log line.
            exception: An exception to record alongside the event. Its type,
                message and stack trace are attached to the record.
        """
        if record:
            self._logger.emit(record)
        else:
            self._logger.emit(
                timestamp=timestamp,
                observed_timestamp=observed_timestamp,
                context=context,
                severity_number=severity_number,
                severity_text=severity_text,
                body=body,
                attributes=attributes,
                event_name=event_name,
                exception=exception,
            )

    def enabled(
        self,
        *,
        context: Context | None = None,
        severity_number: SeverityNumber | None = None,
        event_name: str | None = None,
    ) -> bool:
        """Ask the real logger whether a record would be processed.

        Args:
            context: The context the record would belong to. Defaults to the
                current context.
            severity_number: The severity the record would carry.
            event_name: The name of the event the record would carry.

        Returns:
            Whatever the real logger reports, or ``False`` while no
            :class:`LoggerProvider` has been set globally.
        """
        return self._logger.enabled(
            context=context,
            severity_number=severity_number,
            event_name=event_name,
        )


class LoggerProvider(ABC):
    """
    LoggerProvider is the entry point of the API. It provides access to Logger instances.
    """

    @abstractmethod
    def get_logger(
        self,
        name: str,
        version: str | None = None,
        schema_url: str | None = None,
        attributes: Attributes = None,
    ) -> Logger:
        """Returns a `Logger` for use by the given instrumentation library.

        For any two calls with identical parameters, it is undefined whether the same
        or different `Logger` instances are returned.

        This function may return different `Logger` types (e.g. a no-op logger
        vs. a functional logger).

        Args:
            name: The name of the instrumenting module, package or class.
                This should *not* be the name of the module, package or class that is
                instrumented but the name of the code doing the instrumentation.
                E.g., instead of ``"requests"``, use
                ``"opentelemetry.instrumentation.requests"``.

                For log sources which define a logger name (e.g. logging.Logger.name)
                the Logger Name should be recorded as the instrumentation scope name.

            version: Optional. The version string of the
                instrumenting library.  Usually this should be the same as
                ``importlib.metadata.version(instrumenting_library_name)``.

            schema_url: Optional. Specifies the Schema URL of the emitted telemetry.

            attributes: Optional. Specifies the instrumentation scope attributes to
                associate with emitted telemetry.

        Returns:
            A `Logger` bound to the given instrumentation scope.
        """


class NoOpLoggerProvider(LoggerProvider):
    """The default LoggerProvider used when no LoggerProvider implementation is available."""

    def get_logger(
        self,
        name: str,
        version: str | None = None,
        schema_url: str | None = None,
        attributes: Attributes = None,
    ) -> Logger:
        """Returns a NoOpLogger.

        Args:
            name: The name of the instrumenting module, package or class, not
                the name of the thing being instrumented.
            version: The version string of the instrumenting library.
            schema_url: The Schema URL of the emitted telemetry.
            attributes: The instrumentation scope attributes to associate with
                emitted telemetry.

        Returns:
            A :class:`NoOpLogger` carrying the given scope, which discards
            every record emitted through it.
        """
        return NoOpLogger(name, version=version, schema_url=schema_url, attributes=attributes)


class ProxyLoggerProvider(LoggerProvider):
    """The provider returned before a real one has been set globally.

    It holds no implementation of its own. Every logger this logger provider
    hands out before a real logger provider is set is a :class:`ProxyLogger`,
    which starts out discarding records and switches to the real logger
    provider as soon as :func:`set_logger_provider` installs one. Every logger
    handed out after that call comes from the real logger provider directly.
    This is what lets a library call :func:`get_logger` at import time, before
    the application has configured the SDK.
    """

    def get_logger(
        self,
        name: str,
        version: str | None = None,
        schema_url: str | None = None,
        attributes: Attributes = None,
    ) -> Logger:
        """Return a logger bound to the real provider once one exists.

        Args:
            name: The name of the instrumenting module, package or class, not
                the name of the thing being instrumented.
            version: The version string of the instrumenting library.
            schema_url: The Schema URL of the emitted telemetry.
            attributes: The instrumentation scope attributes to associate with
                emitted telemetry.

        Returns:
            A logger from the global provider when one has been set, and a
            :class:`ProxyLogger` carrying the given scope otherwise.
        """
        if _LOGGER_PROVIDER:
            return _LOGGER_PROVIDER.get_logger(
                name,
                version=version,
                schema_url=schema_url,
                attributes=attributes,
            )
        return ProxyLogger(
            name,
            version=version,
            schema_url=schema_url,
            attributes=attributes,
        )


_LOGGER_PROVIDER_SET_ONCE = Once()
_LOGGER_PROVIDER: LoggerProvider | None = None
_PROXY_LOGGER_PROVIDER = ProxyLoggerProvider()


def get_logger_provider() -> LoggerProvider:
    """Gets the current global :class:`~.LoggerProvider` object.

    Returns:
        The provider set by :func:`set_logger_provider`, or the one named by
        the ``OTEL_PYTHON_LOGGER_PROVIDER`` environment variable. When neither
        is present, a ``ProxyLoggerProvider`` is returned, which starts
        delegating as soon as a provider is set.

    Raises:
        Exception: Whatever loading the entry point named by the environment
            variable raised, since ``_load_provider`` logs it and re-raises. A
            name that matches no installed entry point surfaces as
            :exc:`StopIteration`.
    """
    global _LOGGER_PROVIDER  # pylint: disable=global-variable-not-assigned
    if _LOGGER_PROVIDER is None:
        if _OTEL_PYTHON_LOGGER_PROVIDER not in environ:
            return _PROXY_LOGGER_PROVIDER

        logger_provider: LoggerProvider = _load_provider(  # type: ignore
            _OTEL_PYTHON_LOGGER_PROVIDER, "logger_provider"
        )
        _set_logger_provider(logger_provider, log=False)

    # _LOGGER_PROVIDER will have been set by one thread
    return cast("LoggerProvider", _LOGGER_PROVIDER)


def _set_logger_provider(logger_provider: LoggerProvider, log: bool) -> None:
    """Install the global provider, at most once per process.

    Args:
        logger_provider: The provider to install.
        log: Whether to log a warning when a provider is already installed and
            this call therefore has no effect.
    """

    def set_lp() -> None:
        """Assign the global provider. Called at most once."""
        global _LOGGER_PROVIDER  # pylint: disable=global-statement
        _LOGGER_PROVIDER = logger_provider

    did_set = _LOGGER_PROVIDER_SET_ONCE.do_once(set_lp)

    if log and not did_set:
        _logger.warning("Overriding of current LoggerProvider is not allowed")


def set_logger_provider(logger_provider: LoggerProvider) -> None:
    """Sets the current global :class:`~.LoggerProvider` object.

    This can only be done once, a warning will be logged if any further attempt
    is made.

    Args:
        logger_provider: The provider to install globally.
    """
    _set_logger_provider(logger_provider, log=True)


def get_logger(
    instrumenting_module_name: str,
    instrumenting_library_version: str = "",
    logger_provider: LoggerProvider | None = None,
    schema_url: str | None = None,
    attributes: Attributes = None,
) -> Logger:
    """Returns a `Logger` for use within a python process.

    This function is a convenience wrapper for
    opentelemetry.sdk._logs.LoggerProvider.get_logger.

    If logger_provider param is omitted the current configured one is used.

    Args:
        instrumenting_module_name: The name of the instrumenting module, not
            the name of the thing being instrumented.
        instrumenting_library_version: The version string of the instrumenting
            library.
        logger_provider: The provider to obtain the logger from. Defaults to
            the globally configured one.
        schema_url: The Schema URL of the emitted telemetry.
        attributes: The instrumentation scope attributes to associate with
            emitted telemetry.

    Returns:
        A `Logger` bound to the given instrumentation scope.
    """
    if logger_provider is None:
        logger_provider = get_logger_provider()
    return logger_provider.get_logger(
        instrumenting_module_name,
        instrumenting_library_version,
        schema_url,
        attributes,
    )
