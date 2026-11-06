# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Resetting the API-level provider globals between tests.

The trace, metrics and logs APIs each hold the configured provider in a module
level global, guarded by an ``opentelemetry.util._once.Once`` so that the
corresponding ``set_*_provider`` function takes effect only the first time it is
called. That is the behaviour an application wants and the opposite of what a
test suite wants, because the second test to install a provider would silently
keep the one installed by the first.

The ``reset_*_globals`` functions here reach into those private globals and put
them back to their unset state, and the ``*GlobalsTest`` classes call them from
``setUp`` and ``tearDown`` so a test does not have to. Reaching into private
names is why each of the three functions that assign to those globals carries a
warning against use outside a test suite: nothing here is part of the public API
of the packages it mutates, and a release may move or rename the globals it
assigns to.
"""

import unittest

from opentelemetry import trace as trace_api
from opentelemetry._logs import _internal as logging_api
from opentelemetry.metrics import _internal as metrics_api
from opentelemetry.metrics._internal import _ProxyMeterProvider
from opentelemetry.util._once import Once


# pylint: disable=protected-access
def reset_trace_globals() -> None:
    """Put the trace API globals back to their unset state.

    Clears the configured tracer provider, replaces the proxy tracer provider
    with a fresh one so that a tracer requested after this call is not bound to
    the provider the previous test installed, and resets the ``Once`` guard that
    makes ``opentelemetry.trace.set_tracer_provider`` effective only once.
    After this call, ``set_tracer_provider`` installs a provider again.

    A tracer obtained before this call is not detached by it: a proxy tracer
    caches the real tracer the first time it resolves one, so it keeps sending
    spans to the earlier provider. Request the tracer again after the reset.

    WARNING: only use this for tests. It assigns to private module globals of
    ``opentelemetry.trace``.
    """
    trace_api._TRACER_PROVIDER_SET_ONCE = Once()
    trace_api._TRACER_PROVIDER = None
    trace_api._PROXY_TRACER_PROVIDER = trace_api.ProxyTracerProvider()


# pylint: disable=protected-access
def reset_metrics_globals() -> None:
    """Put the metrics API globals back to their unset state.

    Clears the configured meter provider, replaces the proxy meter provider with
    a fresh one so that a meter requested after this call is not bound to the
    provider the previous test installed, and resets the ``Once`` guard that
    makes ``opentelemetry.metrics.set_meter_provider`` effective only once.

    A meter or instrument obtained before this call is not detached by it: the
    proxy caches the real one the first time it resolves it, so measurements
    keep reaching the earlier provider. Create them again after the reset.

    WARNING: only use this for tests. It assigns to private module globals of
    ``opentelemetry.metrics._internal``.
    """
    metrics_api._METER_PROVIDER_SET_ONCE = Once()  # type: ignore[attr-defined]
    metrics_api._METER_PROVIDER = None  # type: ignore[attr-defined]
    metrics_api._PROXY_METER_PROVIDER = _ProxyMeterProvider()  # type: ignore[attr-defined]


# pylint: disable=protected-access
def reset_logging_globals() -> None:
    """Put the logs API globals back to their unset state.

    Clears the configured logger provider, replaces the proxy logger provider
    with a fresh one so that a logger requested after this call is not bound to
    the provider the previous test installed, and resets the ``Once`` guard that
    makes ``opentelemetry._logs.set_logger_provider`` effective only once.

    A logger obtained before this call is not detached by it: a proxy logger
    caches the real logger the first time it resolves one. Request the logger
    again after the reset.

    WARNING: only use this for tests. It assigns to private module globals of
    ``opentelemetry._logs._internal``.
    """
    logging_api._LOGGER_PROVIDER_SET_ONCE = Once()  # type: ignore[attr-defined]
    logging_api._LOGGER_PROVIDER = None  # type: ignore[attr-defined]
    logging_api._PROXY_LOGGER_PROVIDER = logging_api.ProxyLoggerProvider()  # type: ignore[attr-defined]


# pylint: disable=protected-access
def reset_event_globals() -> None:
    """Deprecated no-op kept for backward compatibility.

    The Events API has been removed, so there are no event globals left to
    reset and this function does nothing. It is still exported so that a test
    suite calling it against an older release of this package keeps importing
    and running. Delete the call rather than keeping it.
    """


class TraceGlobalsTest(unittest.TestCase):
    """Resets trace API globals in setUp/tearDown

    Use as a base class or mixin for your test that modifies trace API globals.
    """

    def setUp(self) -> None:
        """Reset the trace API globals before the test method runs."""
        super().setUp()
        reset_trace_globals()

    def tearDown(self) -> None:
        """Reset the trace API globals again, so the next test starts clean.

        Resetting on both sides means a test that fails part way through still
        leaves the globals unset for whatever runs next.
        """
        super().tearDown()
        reset_trace_globals()


class MetricsGlobalsTest(unittest.TestCase):
    """Resets metrics API globals in setUp/tearDown

    Use as a base class or mixin for your test that modifies metrics API globals.
    """

    def setUp(self) -> None:
        """Reset the metrics API globals before the test method runs."""
        super().setUp()
        reset_metrics_globals()

    def tearDown(self) -> None:
        """Reset the metrics API globals again, so the next test starts clean."""
        super().tearDown()
        reset_metrics_globals()


class LoggingGlobalsTest(unittest.TestCase):
    """Resets logging API globals in setUp/tearDown

    Use as a base class or mixin for your test that modifies logging API globals.
    """

    def setUp(self) -> None:
        """Reset the logs API globals before the test method runs."""
        super().setUp()
        reset_logging_globals()

    def tearDown(self) -> None:
        """Reset the logs API globals again, so the next test starts clean."""
        super().tearDown()
        reset_logging_globals()


class EventsGlobalsTest(unittest.TestCase):
    """Deprecated no-op kept for backward compatibility.

    The Events API has been removed, so there are no event globals left to
    reset and inheriting from this class is the same as inheriting from
    ``unittest.TestCase``. It is still exported so that a test suite naming it
    as a base class keeps importing and running. Replace it with
    ``unittest.TestCase`` rather than keeping it.
    """

    def setUp(self) -> None:  # pylint: disable=useless-parent-delegation
        """Delegate to ``unittest.TestCase``, resetting nothing."""
        super().setUp()

    def tearDown(self) -> None:  # pylint: disable=useless-parent-delegation
        """Delegate to ``unittest.TestCase``, resetting nothing."""
        super().tearDown()
