# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# type: ignore

"""Shared test helpers for the OpenTelemetry Python packages.

This package is published as ``opentelemetry-test-utils``. It is a test
dependency of the other distributions in this repository and of the
instrumentation repositories, never a runtime dependency of library or
application code.

The module itself provides ``TestCase``, a ``unittest.TestCase`` extended with
an ``assertNotRaises`` assertion. The submodules provide the rest: base classes
that reset the API globals and capture spans and metrics in memory
(``opentelemetry.test.test_base``, ``opentelemetry.test.globals_test``), WSGI,
ASGI and HTTP server fixtures (``opentelemetry.test.wsgitestutil``,
``opentelemetry.test.asgitestutil``, ``opentelemetry.test.httptest``), builders
for spans, metrics and samplers (``opentelemetry.test.spantestutil``,
``opentelemetry.test.metrictestutil``, ``opentelemetry.test.samplertestutil``),
propagator doubles (``opentelemetry.test.mock_textmap``), an entry point double
(``opentelemetry.test.mock_test_classes``), helpers for provoking a thread race
(``opentelemetry.test.concurrency_test``), an in-process OTLP/HTTP receiver
(``opentelemetry.test._otlp_test_server``), a semantic convention check against
weaver (``opentelemetry.test.weaver_live_check``), and the version of the
distribution (``opentelemetry.test.version``).
"""

from traceback import format_tb
from unittest import TestCase


class _AssertNotRaisesMixin:
    """Mixin that adds an ``assertNotRaises`` assertion to a test case.

    ``unittest`` has ``assertRaises`` but no inverse, because an unexpected
    exception already fails a test by propagating out of it. ``assertNotRaises``
    exists so that a test can state the expectation explicitly and fail with the
    traceback of the unwanted exception formatted into the failure message,
    rather than with the raw exception.

    Mix it in before ``unittest.TestCase`` in the base class list, so that its
    ``__init__`` runs first and installs the assertion. The ``TestCase`` defined
    in this module already does that.
    """

    class _AssertNotRaises:
        """Callable context manager that fails its test case on given exceptions.

        An instance is bound to ``self.assertNotRaises`` on the test case. It is
        both the callable and the context manager: calling it records the
        exception types to watch for and returns the same instance, which is
        then entered. Entering it without calling it first succeeds, because
        ``__enter__`` does not read the exception types; the omission surfaces
        as an ``AttributeError`` out of ``__exit__``, and only when the block
        raised something.

        The instance is shared across every use within one test case, so nesting
        two ``assertNotRaises`` blocks does not work: the inner call overwrites
        the exception types of the outer one.

        Args:
            test_case: The test case to call ``fail`` on. Stored, not copied, so
                the failure is reported against the running test.
        """

        def __init__(self, test_case):
            """Parameters are documented on the class docstring."""
            self._test_case = test_case

        def __enter__(self):
            """Return this instance so the ``with`` body can run.

            Returns:
                The context manager itself. The value is of no use to the body
                and is returned only because entering a context manager binds a
                value.
            """
            return self

        def __exit__(self, type_, value, tb):  # pylint: disable=invalid-name
            """Fail the test case when one of the watched exceptions was raised.

            The exception type is matched by identity against the types passed
            to ``__call__``, not with ``issubclass``, so a subclass of a watched
            type does not match.

            Args:
                type_: Class of the exception raised in the ``with`` body, or
                    ``None`` when the body completed normally.
                value: The exception instance, or ``None``.
                tb: The traceback of the exception, or ``None``. It is formatted
                    into the failure message.

            Returns:
                Always ``True``, which suppresses whatever exception the ``with``
                body raised, including an exception of a type that was not
                watched.
            """
            if value is not None and type_ in self._exception_types:
                self._test_case.fail("Unexpected exception was raised:\n{}".format("\n".join(format_tb(tb))))

            return True

        def __call__(self, exception, *exceptions):
            """Record the exception types to watch for and return this instance.

            Args:
                exception: An exception class that must not be raised. At least
                    one is required, so that an empty watch list cannot be set
                    by accident.
                *exceptions: Further exception classes that must not be raised.

            Returns:
                The context manager itself, ready to be entered. The types
                recorded here replace any recorded by an earlier call.
            """
            # pylint: disable=attribute-defined-outside-init
            self._exception_types = (exception, *exceptions)
            return self

    def __init__(self, *args, **kwargs):
        """Install ``assertNotRaises`` on this test case.

        Args:
            *args: Forwarded unchanged to the next class in the method
                resolution order, which is the ``unittest.TestCase`` this mixin
                is combined with.
            **kwargs: Forwarded unchanged for the same reason.
        """
        super().__init__(*args, **kwargs)
        # pylint: disable=invalid-name
        self.assertNotRaises = self._AssertNotRaises(self)


class TestCase(_AssertNotRaisesMixin, TestCase):  # pylint: disable=function-redefined
    """A ``unittest.TestCase`` that also provides ``assertNotRaises``.

    This class deliberately shadows the ``unittest.TestCase`` imported in this
    module, so that a test module can switch to it by changing only its import
    and keep writing ``class MyTest(TestCase)``.
    """
