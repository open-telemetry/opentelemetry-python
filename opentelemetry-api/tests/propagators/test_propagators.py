# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# type: ignore

from importlib import reload
from os import environ
from unittest import TestCase
from unittest.mock import Mock, patch

from opentelemetry import trace
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.context.context import Context
from opentelemetry.environment_variables import OTEL_PROPAGATORS
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
)


class TestPropagators(TestCase):
    """Loading tests restore the previous global propagator.

    Each test reloads ``opentelemetry.propagate``. ``tearDown`` puts the
    previous propagator instance back instead of reloading again, so a random
    test order cannot observe this class's environment.
    """

    def setUp(self):
        # pylint: disable=import-outside-toplevel
        from opentelemetry import propagate  # noqa: PLC0415

        self._propagate = propagate
        # pylint: disable=protected-access
        self._previous_textmap = propagate._HTTP_TEXT_FORMAT

    def tearDown(self):
        # pylint: disable=protected-access
        self._propagate._HTTP_TEXT_FORMAT = self._previous_textmap

    @patch("opentelemetry.propagators.composite.CompositePropagator")
    def test_default_composite_propagators(self, mock_compositehttppropagator):
        def test_propagators(propagators):
            propagators = {propagator.__class__ for propagator in propagators}

            self.assertEqual(len(propagators), 2)
            self.assertEqual(
                propagators,
                {TraceContextTextMapPropagator, W3CBaggagePropagator},
            )

        mock_compositehttppropagator.configure_mock(side_effect=test_propagators)

        # pylint: disable=import-outside-toplevel
        import opentelemetry.propagate  # noqa: PLC0415

        reload(opentelemetry.propagate)
        opentelemetry.propagate.get_global_textmap()

    @patch.dict(environ, {OTEL_PROPAGATORS: "None"})
    @patch("opentelemetry.propagators.composite.CompositePropagator")
    def test_none_propagators(self, mock_compositehttppropagator):
        def test_propagators(propagators):
            propagators = {propagator.__class__ for propagator in propagators}

            self.assertEqual(len(propagators), 0)
            self.assertEqual(
                propagators,
                set(),
            )

        mock_compositehttppropagator.configure_mock(side_effect=test_propagators)

        # pylint: disable=import-outside-toplevel
        import opentelemetry.propagate  # noqa: PLC0415

        reload(opentelemetry.propagate)
        opentelemetry.propagate.get_global_textmap()

    @patch.dict(environ, {OTEL_PROPAGATORS: "tracecontext, None"})
    @patch("opentelemetry.propagators.composite.CompositePropagator")
    def test_multiple_propagators_with_none(self, mock_compositehttppropagator):
        def test_propagators(propagators):
            propagators = {propagator.__class__ for propagator in propagators}

            self.assertEqual(len(propagators), 0)
            self.assertEqual(
                propagators,
                set(),
            )

        mock_compositehttppropagator.configure_mock(side_effect=test_propagators)

        # pylint: disable=import-outside-toplevel
        import opentelemetry.propagate  # noqa: PLC0415

        reload(opentelemetry.propagate)
        opentelemetry.propagate.get_global_textmap()

    @patch.dict(environ, {OTEL_PROPAGATORS: "a,  b,   c  "})
    @patch("opentelemetry.propagators.composite.CompositePropagator")
    @patch("opentelemetry.util._importlib_metadata.entry_points")
    def test_non_default_propagators(self, mock_entry_points, mock_compositehttppropagator):
        mock_entry_points.configure_mock(
            side_effect=[
                [
                    Mock(**{"load.return_value": Mock(return_value="a")}),
                ],
                [Mock(**{"load.return_value": Mock(return_value="b")})],
                [Mock(**{"load.return_value": Mock(return_value="c")})],
            ]
        )

        def test_propagators(propagators):
            self.assertEqual(propagators, ["a", "b", "c"])

        mock_compositehttppropagator.configure_mock(side_effect=test_propagators)

        # pylint: disable=import-outside-toplevel
        import opentelemetry.propagate  # noqa: PLC0415

        reload(opentelemetry.propagate)
        opentelemetry.propagate.get_global_textmap()

    @patch.dict(environ, {OTEL_PROPAGATORS: "tracecontext , unknown , baggage"})
    def test_composite_propagators_error(self):
        with self.assertRaises(ValueError) as cm:
            # pylint: disable=import-outside-toplevel
            import opentelemetry.propagate  # noqa: PLC0415

            reload(opentelemetry.propagate)
            opentelemetry.propagate.get_global_textmap()

        self.assertEqual(
            str(cm.exception),
            "Propagator unknown not found. It is either misspelled or not installed.",
        )


class TestGlobalTextMapInitializedOnFirstUse(TestCase):
    """``OTEL_PROPAGATORS`` is applied on the first ``get_global_textmap()`` call.

    Distros import ``opentelemetry.propagate`` and only then set
    ``OTEL_PROPAGATORS`` inside ``configure()``. A previous global propagator
    and the previous environment value are restored in ``tearDown`` so these
    tests do not depend on, or disturb, execution order. ``tearDown`` does not
    reload the module.
    """

    def setUp(self):
        # pylint: disable=import-outside-toplevel
        from opentelemetry import propagate  # noqa: PLC0415

        self._propagate = propagate
        # pylint: disable=protected-access
        self._previous_textmap = propagate._HTTP_TEXT_FORMAT
        self._previous_env = environ.get(OTEL_PROPAGATORS)

    def tearDown(self):
        if self._previous_env is None:
            environ.pop(OTEL_PROPAGATORS, None)
        else:
            environ[OTEL_PROPAGATORS] = self._previous_env
        # Restore the exact instance captured before this test, including when
        # the test reloaded the module. Reloading here would replace the global
        # for every later test.
        # pylint: disable=protected-access
        self._propagate._HTTP_TEXT_FORMAT = self._previous_textmap

    def _reload_with_env_unset(self):
        """Reload as a fresh import that has not seen ``OTEL_PROPAGATORS``."""
        environ.pop(OTEL_PROPAGATORS, None)
        reload(self._propagate)

    @staticmethod
    def _propagator_types(propagator):
        # pylint: disable=protected-access
        return [type(item) for item in propagator._propagators]

    def test_otel_propagators_set_after_import_is_used(self):
        """Distros set ``OTEL_PROPAGATORS`` after this module is imported."""
        self._reload_with_env_unset()
        environ[OTEL_PROPAGATORS] = "baggage,tracecontext"

        propagator = self._propagate.get_global_textmap()

        self.assertEqual(
            self._propagator_types(propagator),
            [W3CBaggagePropagator, TraceContextTextMapPropagator],
        )
        self.assertEqual(propagator.fields, {"baggage", "traceparent", "tracestate"})

    def test_bound_get_global_textmap_sees_env_set_after_import(self):
        """Callers that bound ``get_global_textmap`` at import see the same load."""
        self._reload_with_env_unset()
        early_get = self._propagate.get_global_textmap
        environ[OTEL_PROPAGATORS] = "baggage"

        self.assertEqual(self._propagator_types(early_get()), [W3CBaggagePropagator])

    def test_module_inject_uses_propagators_set_after_import(self):
        """``inject`` resolves the global propagator when it is called."""
        self._reload_with_env_unset()
        environ[OTEL_PROPAGATORS] = "baggage"

        self.assertEqual(self._propagate.get_global_textmap().fields, {"baggage"})
        carrier: dict[str, str] = {}
        self._propagate.inject(carrier)
        self.assertNotIn("traceparent", carrier)

    def test_set_global_textmap_before_load_wins_over_env(self):
        self._reload_with_env_unset()
        # On a lazy global, this call happens before the first read of the env.
        # On an import-time global, reload already loaded the default and this
        # still replaces it. Either way the explicit propagator must stick.
        custom = CompositePropagator([])
        self._propagate.set_global_textmap(custom)
        environ[OTEL_PROPAGATORS] = "tracecontext"

        self.assertIs(self._propagate.get_global_textmap(), custom)

    def test_first_resolution_is_cached_if_env_changes_later(self):
        self._reload_with_env_unset()
        first = self._propagate.get_global_textmap()
        environ[OTEL_PROPAGATORS] = "baggage"
        second = self._propagate.get_global_textmap()

        self.assertIs(first, second)
        self.assertEqual(
            self._propagator_types(first),
            [TraceContextTextMapPropagator, W3CBaggagePropagator],
        )

    def test_default_propagators_when_env_unset(self):
        self._reload_with_env_unset()

        self.assertEqual(
            self._propagator_types(self._propagate.get_global_textmap()),
            [TraceContextTextMapPropagator, W3CBaggagePropagator],
        )

    def test_reload_after_env_is_set_still_honors_it(self):
        """``importlib.reload`` after configure, as some distros do, still works."""
        environ[OTEL_PROPAGATORS] = "baggage"
        reload(self._propagate)

        self.assertEqual(
            self._propagator_types(self._propagate.get_global_textmap()),
            [W3CBaggagePropagator],
        )

    def test_set_global_textmap_replaces_an_already_loaded_propagator(self):
        self._reload_with_env_unset()
        self._propagate.get_global_textmap()
        custom = CompositePropagator([])
        self._propagate.set_global_textmap(custom)

        self.assertIs(self._propagate.get_global_textmap(), custom)

    def test_failed_load_is_not_cached(self):
        """A misspelled propagator does not stick; a later valid value is read."""
        self._reload_with_env_unset()
        environ[OTEL_PROPAGATORS] = "unknown"
        with self.assertRaises(ValueError):
            self._propagate.get_global_textmap()

        environ[OTEL_PROPAGATORS] = "baggage"
        self.assertEqual(
            self._propagator_types(self._propagate.get_global_textmap()),
            [W3CBaggagePropagator],
        )

    def test_concurrent_first_get_resolves_once(self):
        # pylint: disable=import-outside-toplevel
        from threading import Barrier, Thread  # noqa: PLC0415

        self._reload_with_env_unset()
        barrier = Barrier(8)
        resolved = []

        def _resolve():
            barrier.wait()
            resolved.append(self._propagate.get_global_textmap())

        workers = [Thread(target=_resolve) for _ in range(8)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()

        self.assertEqual(len(resolved), 8)
        self.assertTrue(all(item is resolved[0] for item in resolved))


class TestTraceContextTextMapPropagator(TestCase):
    def setUp(self):
        self.propagator = TraceContextTextMapPropagator()

    def traceparent_helper(
        self,
        carrier,
    ):
        # We purposefully start with an empty context so we can test later if anything is added to it.
        initial_context = Context()

        context = self.propagator.extract(carrier, context=initial_context)
        self.assertIsNotNone(context)
        self.assertIsInstance(context, Context)

        return context

    def traceparent_helper_generator(
        self,
        version=0x00,
        trace_id=0x00000000000000000000000000000001,
        span_id=0x0000000000000001,
        trace_flags=0x00,
        suffix="",
    ):
        traceparent = f"{version:02x}-{trace_id:032x}-{span_id:016x}-{trace_flags:02x}{suffix}"
        carrier = {"traceparent": traceparent}
        return self.traceparent_helper(carrier)

    def valid_traceparent_helper(
        self,
        version=0x00,
        trace_id=0x00000000000000000000000000000001,
        span_id=0x0000000000000001,
        trace_flags=0x00,
        suffix="",
        assert_context_msg="A valid traceparent was provided, so the context should be non-empty.",
    ):
        context = self.traceparent_helper_generator(
            version=version,
            trace_id=trace_id,
            span_id=span_id,
            trace_flags=trace_flags,
            suffix=suffix,
        )

        self.assertNotEqual(
            context,
            Context(),
            assert_context_msg,
        )

        span = trace.get_current_span(context)
        self.assertIsNotNone(span)
        self.assertIsInstance(span, trace.span.Span)

        span_context = span.get_span_context()
        self.assertIsNotNone(span_context)
        self.assertIsInstance(span_context, trace.span.SpanContext)

        # Note: No version in SpanContext, it is only used locally in TraceContextTextMapPropagator
        self.assertEqual(span_context.trace_id, trace_id)
        self.assertEqual(span_context.span_id, span_id)
        self.assertEqual(span_context.trace_flags, trace_flags)

        self.assertIsInstance(span_context.trace_state, trace.TraceState)
        self.assertCountEqual(span_context.trace_state, [])
        self.assertEqual(span_context.is_remote, True)

        return context, span, span_context

    def invalid_traceparent_helper(
        self,
        version=0x00,
        trace_id=0x00000000000000000000000000000001,
        span_id=0x0000000000000001,
        trace_flags=0x00,
        suffix="",
        assert_context_msg="An invalid traceparent was provided, so the context should still be empty.",
    ):
        context = self.traceparent_helper_generator(
            version=version,
            trace_id=trace_id,
            span_id=span_id,
            trace_flags=trace_flags,
            suffix=suffix,
        )

        self.assertEqual(
            context,
            Context(),
            assert_context_msg,
        )

        return context

    def test_extract_nothing(self):
        context = self.traceparent_helper(carrier={})
        self.assertEqual(
            context,
            {},
            "We didn't provide a valid traceparent, so we should still have an empty Context.",
        )

    def test_extract_simple_traceparent(self):
        self.valid_traceparent_helper()

    # https://www.w3.org/TR/trace-context/#version
    def test_extract_version_forbidden_ff(self):
        self.invalid_traceparent_helper(
            version=0xFF,
            assert_context_msg="We provided ann invalid traceparent with a forbidden version=0xff, so the context should still be empty.",
        )

    # https://www.w3.org/TR/trace-context/#version-format
    def test_extract_version_00_with_unsupported_suffix(self):
        self.invalid_traceparent_helper(
            suffix="-f00",
            assert_context_msg="We provided an invalid traceparent with version=0x00 and suffix information which is not supported in this version, so the context should still be empty.",
        )

    # https://www.w3.org/TR/trace-context/#versioning-of-traceparent
    # See the parsing of the sampled bit of flags.
    def test_extract_future_version_with_future_suffix_data(self):
        self.valid_traceparent_helper(
            version=0x99,
            suffix="-f00",
            assert_context_msg="We provided a traceparent that is possibly valid in the future with version=0x99 and suffix information, so the context be non-empty.",
        )

    # https://www.w3.org/TR/trace-context/#trace-id
    def test_extract_trace_id_invalid_all_zeros(self):
        self.invalid_traceparent_helper(trace_id=0)

    # https://www.w3.org/TR/trace-context/#parent-id
    def test_extract_span_id_invalid_all_zeros(self):
        self.invalid_traceparent_helper(span_id=0)

    def test_extract_non_decimal_trace_flags(self):
        self.valid_traceparent_helper(trace_flags=0xA0)
