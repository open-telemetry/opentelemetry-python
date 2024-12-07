# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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

from abc import ABC, abstractmethod
from logging import getLogger
from os import environ
from typing import Any, Optional, cast

from opentelemetry._logs.severity import SeverityNumber, std_to_otel
from opentelemetry.context.context import Context
from opentelemetry.environment_variables import _OTEL_PYTHON_LOGGER_PROVIDER
from opentelemetry.util._once import Once
from opentelemetry.util._providers import _load_provider
from opentelemetry.util.types import Attributes

_logger = getLogger(__name__)


class Logger(ABC):
    """Handles emitting events and logs via `LogRecord`."""

    def __init__(
        self,
        name: str,
        version: Optional[str] = None,
        schema_url: Optional[str] = None,
        attributes: Optional[Attributes] = None,
    ) -> None:
        super().__init__()
        self._name = name
        self._version = version
        self._schema_url = schema_url
        self._attributes = attributes

    @abstractmethod
    def is_enabled(
        self,
        severity_number: Optional[SeverityNumber] = None,
        context: Optional[Context] = None,
    ) -> bool:
        """Returns True if the logger is enabled for given severity and context, False otherwise."""

    @abstractmethod
    def emit(
        self,
        name: str = None,
        timestamp: Optional[int] = None,
        observed_timestamp: Optional[int] = None,
        severity_number: Optional[SeverityNumber] = None,
        severity_text: Optional[str] = None,
        context: Optional[Context] = None,
        body: Optional[Any] = None,
        attributes: Optional[Attributes] = None,
    ) -> None:
        """Emits a log record."""


class NoOpLogger(Logger):
    """The default Logger used when no Logger implementation is available.

    All operations are no-op.
    """

    def is_enabled(
        self,
        severity_number: Optional[SeverityNumber] = None,
        context: Optional[Context] = None,
    ) -> bool:
        return False

    def emit(
        self,
        name: str = None,
        timestamp: Optional[int] = None,
        observed_timestamp: Optional[int] = None,
        severity_number: Optional[SeverityNumber] = None,
        severity_text: Optional[str] = None,
        context: Optional[Context] = None,
        body: Optional[Any] = None,
        attributes: Optional[Attributes] = None,
    ) -> None:
        pass


class ProxyLogger(Logger):
    def __init__(  # pylint: disable=super-init-not-called
        self,
        name: str,
        version: Optional[str] = None,
        schema_url: Optional[str] = None,
        attributes: Optional[Attributes] = None,
    ):
        self._name = name
        self._version = version
        self._schema_url = schema_url
        self._attributes = attributes
        self._real_logger: Optional[Logger] = None
        self._noop_logger = NoOpLogger(name)

    @property
    def _logger(self) -> Logger:
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

    def is_enabled(
        self,
        severity_number: Optional[SeverityNumber] = None,
        context: Optional[Context] = None,
    ) -> bool:
        return self._logger.is_enabled(
            severity_number=severity_number, context=context
        )

    def emit(
        self,
        name: str = None,
        timestamp: Optional[int] = None,
        observed_timestamp: Optional[int] = None,
        severity_number: Optional[SeverityNumber] = None,
        severity_text: Optional[str] = None,
        context: Optional[Context] = None,
        body: Optional[Any] = None,
        attributes: Optional[Attributes] = None,
    ) -> None:
        self._logger.emit(
            name=name,
            timestamp=timestamp,
            observed_timestamp=observed_timestamp,
            severity_number=severity_number,
            severity_text=severity_text,
            context=context,
            body=body,
            attributes=attributes,
        )


class LoggerProvider(ABC):
    """
    LoggerProvider is the entry point of the API. It provides access to Logger instances.
    """

    @abstractmethod
    def get_logger(
        self,
        name: str,
        version: Optional[str] = None,
        schema_url: Optional[str] = None,
        attributes: Optional[Attributes] = None,
    ) -> Logger:
        """Returns a `Logger` for use by the given instrumentation library.

        For any two calls it is undefined whether the same or different
        `Logger` instances are returned, even for different library names.

        This function may return different `Logger` types (e.g. a no-op logger
        vs. a functional logger).

        Args:
            name: The name of the instrumenting module.
                ``__name__`` may not be used as this can result in
                different logger names if the loggers are in different files.
                It is better to use a fixed string that can be imported where
                needed and used consistently as the name of the logger.

                This should *not* be the name of the module that is
                instrumented but the name of the module doing the instrumentation.
                E.g., instead of ``"requests"``, use
                ``"opentelemetry.instrumentation.requests"``.

            version: Optional. The version string of the
                instrumenting library.  Usually this should be the same as
                ``importlib.metadata.version(instrumenting_library_name)``.

            schema_url: Optional. Specifies the Schema URL of the emitted telemetry.
        """


class NoOpLoggerProvider(LoggerProvider):
    """The default LoggerProvider used when no LoggerProvider implementation is available."""

    def get_logger(
        self,
        name: str,
        version: Optional[str] = None,
        schema_url: Optional[str] = None,
        attributes: Optional[Attributes] = None,
    ) -> Logger:
        """Returns a NoOpLogger."""
        return NoOpLogger(
            name, version=version, schema_url=schema_url, attributes=attributes
        )


class ProxyLoggerProvider(LoggerProvider):
    def get_logger(
        self,
        name: str,
        version: Optional[str] = None,
        schema_url: Optional[str] = None,
        attributes: Optional[Attributes] = None,
    ) -> Logger:
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
_LOGGER_PROVIDER: Optional[LoggerProvider] = None
_PROXY_LOGGER_PROVIDER = ProxyLoggerProvider()


def get_logger_provider() -> LoggerProvider:
    """Gets the current global :class:`~.LoggerProvider` object."""
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
    def set_lp() -> None:
        global _LOGGER_PROVIDER  # pylint: disable=global-statement
        _LOGGER_PROVIDER = logger_provider

    did_set = _LOGGER_PROVIDER_SET_ONCE.do_once(set_lp)

    if log and not did_set:
        _logger.warning("Overriding of current LoggerProvider is not allowed")


def set_logger_provider(logger_provider: LoggerProvider) -> None:
    """Sets the current global :class:`~.LoggerProvider` object.

    This can only be done once, a warning will be logged if any further attempt
    is made.
    """
    _set_logger_provider(logger_provider, log=True)


def get_logger(
    instrumenting_module_name: str,
    instrumenting_library_version: str = "",
    logger_provider: Optional[LoggerProvider] = None,
    schema_url: Optional[str] = None,
    attributes: Optional[Attributes] = None,
) -> "Logger":
    """Returns a `Logger` for use within a python process.

    This function is a convenience wrapper for
    opentelemetry.sdk._logs.LoggerProvider.get_logger.

    If logger_provider param is omitted the current configured one is used.
    """
    if logger_provider is None:
        logger_provider = get_logger_provider()
    return logger_provider.get_logger(
        instrumenting_module_name,
        instrumenting_library_version,
        schema_url,
        attributes,
    )


__all__ = [
    "Logger",
    "LoggerProvider",
    "LogRecord",
    "NoOpLogger",
    "NoOpLoggerProvider",
    "get_logger",
    "get_logger_provider",
    "set_logger_provider",
    "SeverityNumber",
    "std_to_otel",
]
