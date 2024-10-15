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

# pylint: disable=too-many-lines
# pylint: disable=no-member

import shutil
import subprocess
import unittest
from importlib import reload
from logging import ERROR, WARNING
from random import randint
from time import time_ns
from typing import Optional
from unittest import mock
from unittest.mock import Mock, patch

from opentelemetry import trace as trace_api
from opentelemetry.attributes import BoundedAttributes
from opentelemetry.context import Context
from opentelemetry.sdk import resources, trace
from opentelemetry.sdk.environment_variables import (
    OTEL_ATTRIBUTE_COUNT_LIMIT,
    OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT,
    OTEL_EVENT_ATTRIBUTE_COUNT_LIMIT,
    OTEL_LINK_ATTRIBUTE_COUNT_LIMIT,
    OTEL_SDK_DISABLED,
    OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT,
    OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT,
    OTEL_SPAN_EVENT_COUNT_LIMIT,
    OTEL_SPAN_LINK_COUNT_LIMIT,
    OTEL_TRACES_SAMPLER,
    OTEL_TRACES_SAMPLER_ARG,
)
from opentelemetry.sdk.trace import Resource, TracerProvider
from opentelemetry.sdk.trace.id_generator import RandomIdGenerator
from opentelemetry.sdk.trace.sampling import (
    ALWAYS_OFF,
    ALWAYS_ON,
    Decision,
    ParentBased,
    StaticSampler,
)
from opentelemetry.sdk.util import BoundedDict, ns_to_iso_str
from opentelemetry.sdk.util.instrumentation import InstrumentationInfo
from opentelemetry.test.spantestutil import (
    get_span_with_dropped_attributes_events_links,
    new_tracer,
)
from opentelemetry.trace import (
    Status,
    StatusCode,
    get_tracer,
    set_tracer_provider,
)


class TestTracer(unittest.TestCase):
    def test_no_deprecated_warning(self):
        with self.assertRaises(AssertionError):
            with self.assertWarns(DeprecationWarning):
                TracerProvider(Mock(), Mock()).get_tracer(Mock(), Mock())

        # This is being added here to make sure the filter on
        # InstrumentationInfo does not affect other DeprecationWarnings that
        # may be raised.
        with self.assertWarns(DeprecationWarning):
            BoundedDict(0)

    def test_extends_api(self):
        tracer = new_tracer()
        self.assertIsInstance(tracer, trace.Tracer)
        self.assertIsInstance(tracer, trace_api.Tracer)

    def test_shutdown(self):
        tracer_provider = trace.TracerProvider()

        mock_processor1 = mock.Mock(spec=trace.SpanProcessor)
        tracer_provider.add_span_processor(mock_processor1)

        mock_processor2 = mock.Mock(spec=trace.SpanProcessor)
        tracer_provider.add_span_processor(mock_processor2)

        tracer_provider.shutdown()

        self.assertEqual(mock_processor1.shutdown.call_count, 1)
        self.assertEqual(mock_processor2.shutdown.call_count, 1)

        shutdown_python_code = """
import atexit
from unittest import mock

from opentelemetry.sdk import trace

mock_processor = mock.Mock(spec=trace.SpanProcessor)

def print_shutdown_count():
    print(mock_processor.shutdown.call_count)

# atexit hooks are called in inverse order they are added, so do this before
# creating the tracer
atexit.register(print_shutdown_count)

tracer_provider = trace.TracerProvider({tracer_parameters})
tracer_provider.add_span_processor(mock_processor)

{tracer_shutdown}
"""

        def run_general_code(shutdown_on_exit, explicit_shutdown):
            tracer_parameters = ""
            tracer_shutdown = ""

            if not shutdown_on_exit:
                tracer_parameters = "shutdown_on_exit=False"

            if explicit_shutdown:
                tracer_shutdown = "tracer_provider.shutdown()"

            return subprocess.check_output(
                [
                    # use shutil to avoid calling python outside the
                    # virtualenv on windows.
                    shutil.which("python"),
                    "-c",
                    shutdown_python_code.format(
                        tracer_parameters=tracer_parameters,
                        tracer_shutdown=tracer_shutdown,
                    ),
                ]
            )

        # test default shutdown_on_exit (True)
        out = run_general_code(True, False)
        self.assertTrue(out.startswith(b"1"))

        # test that shutdown is called only once even if Tracer.shutdown is
        # called explicitly
        out = run_general_code(True, True)
        self.assertTrue(out.startswith(b"1"))

        # test shutdown_on_exit=False
        out = run_general_code(False, False)
        self.assertTrue(out.startswith(b"0"))

    def test_tracer_provider_accepts_concurrent_multi_span_processor(self):
        span_processor = trace.ConcurrentMultiSpanProcessor(2)
        tracer_provider = trace.TracerProvider(
            active_span_processor=span_processor
        )

        # pylint: disable=protected-access
        self.assertEqual(
            span_processor, tracer_provider._active_span_processor
        )

    def test_get_tracer_sdk(self):
        tracer_provider = trace.TracerProvider()
        tracer = tracer_provider.get_tracer(
            "module_name",
            "library_version",
            "schema_url",
            {"key1": "value1", "key2": 6},
        )
        # pylint: disable=protected-access
        self.assertEqual(tracer._instrumentation_scope._name, "module_name")
        # pylint: disable=protected-access
        self.assertEqual(
            tracer._instrumentation_scope._version, "library_version"
        )
        # pylint: disable=protected-access
        self.assertEqual(
            tracer._instrumentation_scope._schema_url, "schema_url"
        )
        # pylint: disable=protected-access
        self.assertEqual(
            tracer._instrumentation_scope._attributes,
            {"key1": "value1", "key2": 6},
        )

    @mock.patch.dict("os.environ", {OTEL_SDK_DISABLED: "true"})
    def test_get_tracer_with_sdk_disabled(self):
        tracer_provider = trace.TracerProvider()
        self.assertIsInstance(
            tracer_provider.get_tracer(Mock()), trace_api.NoOpTracer
        )


class TestTracerSampling(unittest.TestCase):
    def tearDown(self):
        reload(trace)

    def test_default_sampler(self):
        tracer = new_tracer()

        # Check that the default tracer creates real spans via the default
        # sampler
        root_span = tracer.start_span(name="root span", context=None)
        ctx = trace_api.set_span_in_context(root_span)
        self.assertIsInstance(root_span, trace.Span)
        child_span = tracer.start_span(name="child span", context=ctx)
        self.assertIsInstance(child_span, trace.Span)
        self.assertTrue(root_span.context.trace_flags.sampled)
        self.assertEqual(
            root_span.get_span_context().trace_flags,
            trace_api.TraceFlags.SAMPLED,
        )
        self.assertEqual(
            child_span.get_span_context().trace_flags,
            trace_api.TraceFlags.SAMPLED,
        )

    def test_default_sampler_type(self):
        tracer_provider = trace.TracerProvider()
        self.verify_default_sampler(tracer_provider)

    @mock.patch("opentelemetry.sdk.trace.sampling._get_from_env_or_default")
    def test_sampler_no_sampling(self, _get_from_env_or_default):
        tracer_provider = trace.TracerProvider(ALWAYS_OFF)
        tracer = tracer_provider.get_tracer(__name__)

        # Check that the default tracer creates no-op spans if the sampler
        # decides not to sampler
        root_span = tracer.start_span(name="root span", context=None)
        ctx = trace_api.set_span_in_context(root_span)
        self.assertIsInstance(root_span, trace_api.NonRecordingSpan)
        child_span = tracer.start_span(name="child span", context=ctx)
        self.assertIsInstance(child_span, trace_api.NonRecordingSpan)
        self.assertEqual(
            root_span.get_span_context().trace_flags,
            trace_api.TraceFlags.DEFAULT,
        )
        self.assertEqual(
            child_span.get_span_context().trace_flags,
            trace_api.TraceFlags.DEFAULT,
        )
        self.assertFalse(_get_from_env_or_default.called)

    @mock.patch.dict("os.environ", {OTEL_TRACES_SAMPLER: "always_off"})
    def test_sampler_with_env(self):
        # pylint: disable=protected-access
        reload(trace)
        tracer_provider = trace.TracerProvider()
        self.assertIsInstance(tracer_provider.sampler, StaticSampler)
        self.assertEqual(tracer_provider.sampler._decision, Decision.DROP)

        tracer = tracer_provider.get_tracer(__name__)

        root_span = tracer.start_span(name="root span", context=None)
        # Should be no-op
        self.assertIsInstance(root_span, trace_api.NonRecordingSpan)

    @mock.patch.dict(
        "os.environ",
        {
            OTEL_TRACES_SAMPLER: "parentbased_traceidratio",
            OTEL_TRACES_SAMPLER_ARG: "0.25",
        },
    )
    def test_ratio_sampler_with_env(self):
        # pylint: disable=protected-access
        reload(trace)
        tracer_provider = trace.TracerProvider()
        self.assertIsInstance(tracer_provider.sampler, ParentBased)
        self.assertEqual(tracer_provider.sampler._root.rate, 0.25)

    def verify_default_sampler(self, tracer_provider):
        self.assertIsInstance(tracer_provider.sampler, ParentBased)
        # pylint: disable=protected-access
        self.assertEqual(tracer_provider.sampler._root, ALWAYS_ON)


class TestSpanCreation(unittest.TestCase):
    def test_start_span_invalid_spancontext(self):
        """If an invalid span context is passed as the parent, the created
        span should use a new span id.

        Invalid span contexts should also not be added as a parent. This
        eliminates redundant error handling logic in exporters.
        """
        tracer = new_tracer()
        parent_context = trace_api.set_span_in_context(
            trace_api.INVALID_SPAN_CONTEXT
        )
        new_span = tracer.start_span("root", context=parent_context)
        self.assertTrue(new_span.context.is_valid)
        self.assertIsNone(new_span.parent)

    def test_instrumentation_info(self):
        tracer_provider = trace.TracerProvider()
        schema_url = "https://opentelemetry.io/schemas/1.3.0"
        tracer1 = tracer_provider.get_tracer("instr1")
        tracer2 = tracer_provider.get_tracer("instr2", "1.3b3", schema_url)
        span1 = tracer1.start_span("s1")
        span2 = tracer2.start_span("s2")
        with self.assertWarns(DeprecationWarning):
            self.assertEqual(
                span1.instrumentation_info, InstrumentationInfo("instr1", "")
            )
        with self.assertWarns(DeprecationWarning):
            self.assertEqual(
                span2.instrumentation_info,
                InstrumentationInfo("instr2", "1.3b3", schema_url),
            )

        with self.assertWarns(DeprecationWarning):
            self.assertEqual(span2.instrumentation_info.schema_url, schema_url)
        with self.assertWarns(DeprecationWarning):
            self.assertEqual(span2.instrumentation_info.version, "1.3b3")
        with self.assertWarns(DeprecationWarning):
            self.assertEqual(span2.instrumentation_info.name, "instr2")

        with self.assertWarns(DeprecationWarning):
            self.assertLess(
                span1.instrumentation_info, span2.instrumentation_info
            )  # Check sortability.

    def test_invalid_instrumentation_info(self):
        tracer_provider = trace.TracerProvider()
        with self.assertLogs(level=ERROR):
            tracer1 = tracer_provider.get_tracer("")
        with self.assertLogs(level=ERROR):
            tracer2 = tracer_provider.get_tracer(None)

        self.assertIsInstance(
            tracer1.instrumentation_info, InstrumentationInfo
        )
        span1 = tracer1.start_span("foo")
        self.assertTrue(span1.is_recording())
        self.assertEqual(tracer1.instrumentation_info.schema_url, "")
        self.assertEqual(tracer1.instrumentation_info.version, "")
        self.assertEqual(tracer1.instrumentation_info.name, "")

        self.assertIsInstance(
            tracer2.instrumentation_info, InstrumentationInfo
        )
        span2 = tracer2.start_span("bar")
        self.assertTrue(span2.is_recording())
        self.assertEqual(tracer2.instrumentation_info.schema_url, "")
        self.assertEqual(tracer2.instrumentation_info.version, "")
        self.assertEqual(tracer2.instrumentation_info.name, "")

        self.assertEqual(
            tracer1.instrumentation_info, tracer2.instrumentation_info
        )

    def test_span_processor_for_source(self):
        tracer_provider = trace.TracerProvider()
        tracer1 = tracer_provider.get_tracer("instr1")
        tracer2 = tracer_provider.get_tracer("instr2", "1.3b3")
        span1 = tracer1.start_span("s1")
        span2 = tracer2.start_span("s2")

        # pylint:disable=protected-access
        self.assertIs(
            span1._span_processor, tracer_provider._active_span_processor
        )
        self.assertIs(
            span2._span_processor, tracer_provider._active_span_processor
        )

    def test_start_span_implicit(self):
        tracer = new_tracer()

        self.assertEqual(trace_api.get_current_span(), trace_api.INVALID_SPAN)

        root = tracer.start_span("root")
        self.assertIsNotNone(root.start_time)
        self.assertIsNone(root.end_time)
        self.assertEqual(root.kind, trace_api.SpanKind.INTERNAL)

        with trace_api.use_span(root, True):
            self.assertIs(trace_api.get_current_span(), root)

            with tracer.start_span(
                "child", kind=trace_api.SpanKind.CLIENT
            ) as child:
                self.assertIs(child.parent, root.get_span_context())
                self.assertEqual(child.kind, trace_api.SpanKind.CLIENT)

                self.assertIsNotNone(child.start_time)
                self.assertIsNone(child.end_time)

                # The new child span should inherit the parent's context but
                # get a new span ID.
                root_context = root.get_span_context()
                child_context = child.get_span_context()
                self.assertEqual(root_context.trace_id, child_context.trace_id)
                self.assertNotEqual(
                    root_context.span_id, child_context.span_id
                )
                self.assertEqual(
                    root_context.trace_state, child_context.trace_state
                )
                self.assertEqual(
                    root_context.trace_flags, child_context.trace_flags
                )

                # Verify start_span() did not set the current span.
                self.assertIs(trace_api.get_current_span(), root)

            self.assertIsNotNone(child.end_time)

        self.assertEqual(trace_api.get_current_span(), trace_api.INVALID_SPAN)
        self.assertIsNotNone(root.end_time)

    def test_start_span_explicit(self):
        tracer = new_tracer()

        other_parent = trace._Span(
            "name",
            trace_api.SpanContext(
                trace_id=0x000000000000000000000000DEADBEEF,
                span_id=0x00000000DEADBEF0,
                is_remote=False,
                trace_flags=trace_api.TraceFlags(trace_api.TraceFlags.SAMPLED),
            ),
        )

        other_parent_context = trace_api.set_span_in_context(other_parent)

        self.assertEqual(trace_api.get_current_span(), trace_api.INVALID_SPAN)

        root = tracer.start_span("root")
        self.assertIsNotNone(root.start_time)
        self.assertIsNone(root.end_time)

        # Test with the implicit root span
        with trace_api.use_span(root, True):
            self.assertIs(trace_api.get_current_span(), root)

            with tracer.start_span("stepchild", other_parent_context) as child:
                # The child's parent should be the one passed in,
                # not the current span.
                self.assertNotEqual(child.parent, root)
                self.assertIs(child.parent, other_parent.get_span_context())

                self.assertIsNotNone(child.start_time)
                self.assertIsNone(child.end_time)

                # The child should inherit its context from the explicit
                # parent, not the current span.
                child_context = child.get_span_context()
                self.assertEqual(
                    other_parent.get_span_context().trace_id,
                    child_context.trace_id,
                )
                self.assertNotEqual(
                    other_parent.get_span_context().span_id,
                    child_context.span_id,
                )
                self.assertEqual(
                    other_parent.get_span_context().trace_state,
                    child_context.trace_state,
                )
                self.assertEqual(
                    other_parent.get_span_context().trace_flags,
                    child_context.trace_flags,
                )

                # Verify start_span() did not set the current span.
                self.assertIs(trace_api.get_current_span(), root)

            # Verify ending the child did not set the current span.
            self.assertIs(trace_api.get_current_span(), root)
            self.assertIsNotNone(child.end_time)

    def test_start_as_current_span_implicit(self):
        tracer = new_tracer()

        self.assertEqual(trace_api.get_current_span(), trace_api.INVALID_SPAN)

        with tracer.start_as_current_span("root") as root:
            self.assertIs(trace_api.get_current_span(), root)

            with tracer.start_as_current_span("child") as child:
                self.assertIs(trace_api.get_current_span(), child)
                self.assertIs(child.parent, root.get_span_context())

            # After exiting the child's scope the parent should become the
            # current span again.
            self.assertIs(trace_api.get_current_span(), root)
            self.assertIsNotNone(child.end_time)

        self.assertEqual(trace_api.get_current_span(), trace_api.INVALID_SPAN)
        self.assertIsNotNone(root.end_time)

    def test_start_as_current_span_explicit(self):
        tracer = new_tracer()

        other_parent = trace._Span(
            "name",
            trace_api.SpanContext(
                trace_id=0x000000000000000000000000DEADBEEF,
                span_id=0x00000000DEADBEF0,
                is_remote=False,
                trace_flags=trace_api.TraceFlags(trace_api.TraceFlags.SAMPLED),
            ),
        )
        other_parent_ctx = trace_api.set_span_in_context(other_parent)

        self.assertEqual(trace_api.get_current_span(), trace_api.INVALID_SPAN)

        # Test with the implicit root span
        with tracer.start_as_current_span("root") as root:
            self.assertIs(trace_api.get_current_span(), root)

            self.assertIsNotNone(root.start_time)
            self.assertIsNone(root.end_time)

            with tracer.start_as_current_span(
                "stepchild", other_parent_ctx
            ) as child:
                # The child should become the current span as usual, but its
                # parent should be the one passed in, not the
                # previously-current span.
                self.assertIs(trace_api.get_current_span(), child)
                self.assertNotEqual(child.parent, root)
                self.assertIs(child.parent, other_parent.get_span_context())

            # After exiting the child's scope the last span on the stack should
            # become current, not the child's parent.
            self.assertNotEqual(trace_api.get_current_span(), other_parent)
            self.assertIs(trace_api.get_current_span(), root)
            self.assertIsNotNone(child.end_time)

    def test_start_as_current_span_decorator(self):
        tracer = new_tracer()

        self.assertEqual(trace_api.get_current_span(), trace_api.INVALID_SPAN)

        @tracer.start_as_current_span("root")
        def func():
            root = trace_api.get_current_span()

            with tracer.start_as_current_span("child") as child:
                self.assertIs(trace_api.get_current_span(), child)
                self.assertIs(child.parent, root.get_span_context())

            # After exiting the child's scope the parent should become the
            # current span again.
            self.assertIs(trace_api.get_current_span(), root)
            self.assertIsNotNone(child.end_time)

            return root

        root1 = func()

        self.assertEqual(trace_api.get_current_span(), trace_api.INVALID_SPAN)
        self.assertIsNotNone(root1.end_time)

        # Second call must create a new span
        root2 = func()
        self.assertEqual(trace_api.get_current_span(), trace_api.INVALID_SPAN)
        self.assertIsNotNone(root2.end_time)
        self.assertIsNot(root1, root2)

    def test_start_as_current_span_no_end_on_exit(self):
        tracer = new_tracer()

        with tracer.start_as_current_span("root", end_on_exit=False) as root:
            self.assertIsNone(root.end_time)

        self.assertIsNone(root.end_time)

    def test_explicit_span_resource(self):
        resource = resources.Resource.create({})
        tracer_provider = trace.TracerProvider(resource=resource)
        tracer = tracer_provider.get_tracer(__name__)
        span = tracer.start_span("root")
        self.assertIs(span.resource, resource)

    def test_default_span_resource(self):
        tracer_provider = trace.TracerProvider()
        tracer = tracer_provider.get_tracer(__name__)
        span = tracer.start_span("root")
        # pylint: disable=protected-access
        self.assertIsInstance(span.resource, resources.Resource)
        self.assertEqual(
            span.resource.attributes.get(resources.SERVICE_NAME),
            "unknown_service",
        )
        self.assertEqual(
            span.resource.attributes.get(resources.TELEMETRY_SDK_LANGUAGE),
            "python",
        )
        self.assertEqual(
            span.resource.attributes.get(resources.TELEMETRY_SDK_NAME),
            "opentelemetry",
        )
        self.assertEqual(
            span.resource.attributes.get(resources.TELEMETRY_SDK_VERSION),
            resources._OPENTELEMETRY_SDK_VERSION,
        )

    def test_span_context_remote_flag(self):
        tracer = new_tracer()

        span = tracer.start_span("foo")
        self.assertFalse(span.context.is_remote)

    def test_disallow_direct_span_creation(self):
        with self.assertRaises(TypeError):
            # pylint: disable=abstract-class-instantiated
            trace.Span("name", mock.Mock(spec=trace_api.SpanContext))

    def test_surplus_span_links(self):
        # pylint: disable=protected-access
        max_links = trace.SpanLimits().max_links
        links = [
            trace_api.Link(trace_api.SpanContext(0x1, idx, is_remote=False))
            for idx in range(0, 16 + max_links)
        ]
        tracer = new_tracer()
        with tracer.start_as_current_span("span", links=links) as root:
            self.assertEqual(len(root.links), max_links)

    def test_surplus_span_attributes(self):
        # pylint: disable=protected-access
        max_attrs = trace.SpanLimits().max_span_attributes
        attributes = {str(idx): idx for idx in range(0, 16 + max_attrs)}
        tracer = new_tracer()
        with tracer.start_as_current_span(
            "span", attributes=attributes
        ) as root:
            self.assertEqual(len(root.attributes), max_attrs)


class TestReadableSpan(unittest.TestCase):
    def test_links(self):
        span = trace.ReadableSpan("test")
        self.assertEqual(span.links, ())

        span = trace.ReadableSpan(
            "test",
            links=[trace_api.Link(context=trace_api.INVALID_SPAN_CONTEXT)] * 2,
        )
        self.assertEqual(len(span.links), 2)
        for link in span.links:
            self.assertFalse(link.context.is_valid)

    def test_events(self):
        span = trace.ReadableSpan("test")
        self.assertEqual(span.events, ())
        events = [
            trace.Event("foo1", {"bar1": "baz1"}),
            trace.Event("foo2", {"bar2": "baz2"}),
        ]
        span = trace.ReadableSpan("test", events=events)
        self.assertEqual(span.events, tuple(events))

    def test_event_dropped_attributes(self):
        event1 = trace.Event(
            "foo1", BoundedAttributes(0, attributes={"bar1": "baz1"})
        )
        self.assertEqual(event1.dropped_attributes, 1)

        event2 = trace.Event("foo2", {"bar2": "baz2"})
        self.assertEqual(event2.dropped_attributes, 0)

    def test_link_dropped_attributes(self):
        link1 = trace_api.Link(
            mock.Mock(spec=trace_api.SpanContext),
            BoundedAttributes(0, attributes={"bar1": "baz1"}),
        )
        self.assertEqual(link1.dropped_attributes, 1)

        link2 = trace_api.Link(
            mock.Mock(spec=trace_api.SpanContext),
            {"bar2": "baz2"},
        )
        self.assertEqual(link2.dropped_attributes, 0)


class DummyError(Exception):
    pass


class TestSpan(unittest.TestCase):
    # pylint: disable=too-many-public-methods

    def setUp(self):
        self.tracer = new_tracer()

    def test_basic_span(self):
        span = trace._Span("name", mock.Mock(spec=trace_api.SpanContext))
        self.assertEqual(span.name, "name")

    def test_attributes(self):
        with self.tracer.start_as_current_span("root") as root:
            root.set_attributes(
                {
                    "http.request.method": "GET",
                    "url.full": "https://example.com:779/path/12/?q=d#123",
                }
            )

            root.set_attribute("http.response.status_code", 200)
            root.set_attribute("http.status_text", "OK")
            root.set_attribute("misc.pi", 3.14)

            # Setting an attribute with the same key as an existing attribute
            # SHOULD overwrite the existing attribute's value.
            root.set_attribute("attr-key", "attr-value1")
            root.set_attribute("attr-key", "attr-value2")

            root.set_attribute("empty-list", [])
            list_of_bools = [True, True, False]
            root.set_attribute("list-of-bools", list_of_bools)
            list_of_numerics = [123, 314, 0]
            root.set_attribute("list-of-numerics", list_of_numerics)

            self.assertEqual(len(root.attributes), 9)
            self.assertEqual(root.attributes["http.request.method"], "GET")
            self.assertEqual(
                root.attributes["url.full"],
                "https://example.com:779/path/12/?q=d#123",
            )
            self.assertEqual(root.attributes["http.response.status_code"], 200)
            self.assertEqual(root.attributes["http.status_text"], "OK")
            self.assertEqual(root.attributes["misc.pi"], 3.14)
            self.assertEqual(root.attributes["attr-key"], "attr-value2")
            self.assertEqual(root.attributes["empty-list"], ())
            self.assertEqual(
                root.attributes["list-of-bools"], (True, True, False)
            )
            list_of_bools.append(False)
            self.assertEqual(
                root.attributes["list-of-bools"], (True, True, False)
            )
            self.assertEqual(
                root.attributes["list-of-numerics"], (123, 314, 0)
            )
            list_of_numerics.append(227)
            self.assertEqual(
                root.attributes["list-of-numerics"], (123, 314, 0)
            )

        attributes = {
            "attr-key": "val",
            "attr-key2": "val2",
            "attr-in-both": "span-attr",
        }
        with self.tracer.start_as_current_span(
            "root2", attributes=attributes
        ) as root:
            self.assertEqual(len(root.attributes), 3)
            self.assertEqual(root.attributes["attr-key"], "val")
            self.assertEqual(root.attributes["attr-key2"], "val2")
            self.assertEqual(root.attributes["attr-in-both"], "span-attr")

    def test_invalid_attribute_values(self):
        with self.tracer.start_as_current_span("root") as root:
            with self.assertLogs(level=WARNING):
                root.set_attributes(
                    {"correct-value": "foo", "non-primitive-data-type": {}}
                )

            with self.assertLogs(level=WARNING):
                root.set_attribute("non-primitive-data-type", {})
            with self.assertLogs(level=WARNING):
                root.set_attribute(
                    "list-of-mixed-data-types-numeric-first",
                    [123, False, "string"],
                )
            with self.assertLogs(level=WARNING):
                root.set_attribute(
                    "list-of-mixed-data-types-non-numeric-first",
                    [False, 123, "string"],
                )
            with self.assertLogs(level=WARNING):
                root.set_attribute(
                    "list-with-non-primitive-data-type", [{}, 123]
                )
            with self.assertLogs(level=WARNING):
                root.set_attribute("list-with-numeric-and-bool", [1, True])

            with self.assertLogs(level=WARNING):
                root.set_attribute("", 123)
            with self.assertLogs(level=WARNING):
                root.set_attribute(None, 123)

            self.assertEqual(len(root.attributes), 1)
            self.assertEqual(root.attributes["correct-value"], "foo")

    def test_byte_type_attribute_value(self):
        with self.tracer.start_as_current_span("root") as root:
            with self.assertLogs(level=WARNING):
                root.set_attribute(
                    "invalid-byte-type-attribute",
                    b"\xd8\xe1\xb7\xeb\xa8\xe5 \xd2\xb7\xe1",
                )
                self.assertFalse(
                    "invalid-byte-type-attribute" in root.attributes
                )

            root.set_attribute("valid-byte-type-attribute", b"valid byte")
            self.assertTrue(
                isinstance(root.attributes["valid-byte-type-attribute"], str)
            )

    def test_sampling_attributes(self):
        sampling_attributes = {
            "sampler-attr": "sample-val",
            "attr-in-both": "decision-attr",
        }
        tracer_provider = trace.TracerProvider(
            StaticSampler(Decision.RECORD_AND_SAMPLE)
        )

        self.tracer = tracer_provider.get_tracer(__name__)

        with self.tracer.start_as_current_span(
            name="root2", attributes=sampling_attributes
        ) as root:
            self.assertEqual(len(root.attributes), 2)
            self.assertEqual(root.attributes["sampler-attr"], "sample-val")
            self.assertEqual(root.attributes["attr-in-both"], "decision-attr")
            self.assertEqual(
                root.get_span_context().trace_flags,
                trace_api.TraceFlags.SAMPLED,
            )

    def test_events(self):
        self.assertEqual(trace_api.get_current_span(), trace_api.INVALID_SPAN)

        with self.tracer.start_as_current_span("root") as root:
            # only event name
            root.add_event("event0")

            # event name and attributes
            root.add_event(
                "event1", {"name": "pluto", "some_bools": [True, False]}
            )

            # event name, attributes and timestamp
            now = time_ns()
            root.add_event("event2", {"name": ["birthday"]}, now)

            mutable_list = ["original_contents"]
            root.add_event("event3", {"name": mutable_list})

            self.assertEqual(len(root.events), 4)

            self.assertEqual(root.events[0].name, "event0")
            self.assertEqual(root.events[0].attributes, {})

            self.assertEqual(root.events[1].name, "event1")
            self.assertEqual(
                root.events[1].attributes,
                {"name": "pluto", "some_bools": (True, False)},
            )

            self.assertEqual(root.events[2].name, "event2")
            self.assertEqual(
                root.events[2].attributes, {"name": ("birthday",)}
            )
            self.assertEqual(root.events[2].timestamp, now)

            self.assertEqual(root.events[3].name, "event3")
            self.assertEqual(
                root.events[3].attributes, {"name": ("original_contents",)}
            )
            mutable_list = ["new_contents"]
            self.assertEqual(
                root.events[3].attributes, {"name": ("original_contents",)}
            )

    def test_events_are_immutable(self):
        event_properties = [
            prop for prop in dir(trace.EventBase) if not prop.startswith("_")
        ]

        with self.tracer.start_as_current_span("root") as root:
            root.add_event("event0", {"name": ["birthday"]})
            event = root.events[0]

            for prop in event_properties:
                with self.assertRaises(AttributeError):
                    setattr(event, prop, "something")

    def test_event_attributes_are_immutable(self):
        with self.tracer.start_as_current_span("root") as root:
            root.add_event("event0", {"name": ["birthday"]})
            event = root.events[0]

            with self.assertRaises(TypeError):
                event.attributes["name"][0] = "happy"

            with self.assertRaises(TypeError):
                event.attributes["name"] = "hello"

    def test_invalid_event_attributes(self):
        self.assertEqual(trace_api.get_current_span(), trace_api.INVALID_SPAN)

        with self.tracer.start_as_current_span("root") as root:
            with self.assertLogs(level=WARNING):
                root.add_event(
                    "event0", {"attr1": True, "attr2": ["hi", False]}
                )
            with self.assertLogs(level=WARNING):
                root.add_event("event0", {"attr1": {}})
            with self.assertLogs(level=WARNING):
                root.add_event("event0", {"attr1": [[True]]})
            with self.assertLogs(level=WARNING):
                root.add_event("event0", {"attr1": [{}], "attr2": [1, 2]})

            self.assertEqual(len(root.events), 4)
            self.assertEqual(root.events[0].attributes, {"attr1": True})
            self.assertEqual(root.events[1].attributes, {})
            self.assertEqual(root.events[2].attributes, {})
            self.assertEqual(root.events[3].attributes, {"attr2": (1, 2)})

    def test_links(self):
        id_generator = RandomIdGenerator()
        other_context1 = trace_api.SpanContext(
            trace_id=id_generator.generate_trace_id(),
            span_id=id_generator.generate_span_id(),
            is_remote=False,
        )
        other_context2 = trace_api.SpanContext(
            trace_id=id_generator.generate_trace_id(),
            span_id=id_generator.generate_span_id(),
            is_remote=False,
        )

        links = (
            trace_api.Link(other_context1),
            trace_api.Link(other_context2, {"name": "neighbor"}),
        )
        with self.tracer.start_as_current_span("root", links=links) as root:
            self.assertEqual(len(root.links), 2)
            self.assertEqual(
                root.links[0].context.trace_id, other_context1.trace_id
            )
            self.assertEqual(
                root.links[0].context.span_id, other_context1.span_id
            )
            self.assertEqual(0, len(root.links[0].attributes))
            self.assertEqual(
                root.links[1].context.trace_id, other_context2.trace_id
            )
            self.assertEqual(
                root.links[1].context.span_id, other_context2.span_id
            )
            self.assertEqual(root.links[1].attributes, {"name": "neighbor"})

            with self.assertRaises(TypeError):
                root.links[1].attributes["name"] = "new_neighbour"

    def test_add_link(self):
        id_generator = RandomIdGenerator()
        other_context = trace_api.SpanContext(
            trace_id=id_generator.generate_trace_id(),
            span_id=id_generator.generate_span_id(),
            is_remote=False,
        )

        with self.tracer.start_as_current_span("root") as root:
            root.add_link(other_context, {"name": "neighbor"})

            self.assertEqual(len(root.links), 1)
            self.assertEqual(
                root.links[0].context.trace_id, other_context.trace_id
            )
            self.assertEqual(
                root.links[0].context.span_id, other_context.span_id
            )
            self.assertEqual(root.links[0].attributes, {"name": "neighbor"})

            with self.assertRaises(TypeError):
                root.links[0].attributes["name"] = "new_neighbour"

    def test_add_link_with_invalid_span_context(self):
        other_context = trace_api.INVALID_SPAN_CONTEXT

        with self.tracer.start_as_current_span("root") as root:
            root.add_link(other_context)
            root.add_link(None)
            self.assertEqual(len(root.links), 0)

        with self.tracer.start_as_current_span(
            "root", links=[trace_api.Link(other_context), None]
        ) as root:
            self.assertEqual(len(root.links), 0)

    def test_add_link_with_invalid_span_context_with_attributes(self):
        invalid_context = trace_api.INVALID_SPAN_CONTEXT

        with self.tracer.start_as_current_span("root") as root:
            root.add_link(invalid_context)
            root.add_link(invalid_context, {"name": "neighbor"})
            self.assertEqual(len(root.links), 1)
            self.assertEqual(root.links[0].attributes, {"name": "neighbor"})

        with self.tracer.start_as_current_span(
            "root",
            links=[
                trace_api.Link(invalid_context, {"name": "neighbor"}),
                trace_api.Link(invalid_context),
            ],
        ) as root:
            self.assertEqual(len(root.links), 1)

    def test_add_link_with_invalid_span_context_with_tracestate(self):
        invalid_context = trace.SpanContext(
            trace_api.INVALID_TRACE_ID,
            trace_api.INVALID_SPAN_ID,
            is_remote=False,
            trace_state="foo=bar",
        )

        with self.tracer.start_as_current_span("root") as root:
            root.add_link(invalid_context)
            root.add_link(trace_api.INVALID_SPAN_CONTEXT)
            self.assertEqual(len(root.links), 1)
            self.assertEqual(root.links[0].context.trace_state, "foo=bar")

        with self.tracer.start_as_current_span(
            "root",
            links=[
                trace_api.Link(invalid_context),
                trace_api.Link(trace_api.INVALID_SPAN_CONTEXT),
            ],
        ) as root:
            self.assertEqual(len(root.links), 1)

    def test_update_name(self):
        with self.tracer.start_as_current_span("root") as root:
            # name
            root.update_name("toor")
            self.assertEqual(root.name, "toor")

    def test_start_span(self):
        """Start twice, end a not started"""
        span = trace._Span("name", mock.Mock(spec=trace_api.SpanContext))

        # end not started span
        self.assertRaises(RuntimeError, span.end)

        span.start()
        start_time = span.start_time
        with self.assertLogs(level=WARNING):
            span.start()
        self.assertEqual(start_time, span.start_time)

        self.assertIsNotNone(span.status)
        self.assertIs(span.status.status_code, trace_api.StatusCode.UNSET)

        # status
        new_status = trace_api.status.Status(
            trace_api.StatusCode.ERROR, "Test description"
        )
        span.set_status(new_status)
        self.assertIs(span.status.status_code, trace_api.StatusCode.ERROR)
        self.assertIs(span.status.description, "Test description")

    def test_start_accepts_context(self):
        # pylint: disable=no-self-use
        span_processor = mock.Mock(spec=trace.SpanProcessor)
        span = trace._Span(
            "name",
            mock.Mock(spec=trace_api.SpanContext),
            span_processor=span_processor,
        )
        context = Context()
        span.start(parent_context=context)
        span_processor.on_start.assert_called_once_with(
            span, parent_context=context
        )

    def test_span_override_start_and_end_time(self):
        """Span sending custom start_time and end_time values"""
        span = trace._Span("name", mock.Mock(spec=trace_api.SpanContext))
        start_time = 123
        span.start(start_time)
        self.assertEqual(start_time, span.start_time)
        end_time = 456
        span.end(end_time)
        self.assertEqual(end_time, span.end_time)

    def test_span_set_status(self):
        span1 = self.tracer.start_span("span1")
        span1.set_status(Status(status_code=StatusCode.ERROR))
        self.assertEqual(span1.status.status_code, StatusCode.ERROR)
        self.assertEqual(span1.status.description, None)

        span2 = self.tracer.start_span("span2")
        span2.set_status(
            Status(status_code=StatusCode.ERROR, description="desc")
        )
        self.assertEqual(span2.status.status_code, StatusCode.ERROR)
        self.assertEqual(span2.status.description, "desc")

        span3 = self.tracer.start_span("span3")
        span3.set_status(StatusCode.ERROR)
        self.assertEqual(span3.status.status_code, StatusCode.ERROR)
        self.assertEqual(span3.status.description, None)

        span4 = self.tracer.start_span("span4")
        span4.set_status(StatusCode.ERROR, "span4 desc")
        self.assertEqual(span4.status.status_code, StatusCode.ERROR)
        self.assertEqual(span4.status.description, "span4 desc")

        span5 = self.tracer.start_span("span5")
        with self.assertLogs(level=WARNING):
            span5.set_status(
                Status(status_code=StatusCode.ERROR, description="desc"),
                description="ignored",
            )
        self.assertEqual(span5.status.status_code, StatusCode.ERROR)
        self.assertEqual(span5.status.description, "desc")

    def test_ended_span(self):
        """Events, attributes are not allowed after span is ended"""

        root = self.tracer.start_span("root")

        # everything should be empty at the beginning
        self.assertEqual(len(root.attributes), 0)
        self.assertEqual(len(root.events), 0)
        self.assertEqual(len(root.links), 0)

        # call end first time
        root.end()
        end_time0 = root.end_time

        # call it a second time
        with self.assertLogs(level=WARNING):
            root.end()
        # end time shouldn't be changed
        self.assertEqual(end_time0, root.end_time)

        with self.assertLogs(level=WARNING):
            root.set_attribute("http.request.method", "GET")
        self.assertEqual(len(root.attributes), 0)

        with self.assertLogs(level=WARNING):
            root.add_event("event1")
        self.assertEqual(len(root.events), 0)

        with self.assertLogs(level=WARNING):
            root.update_name("xxx")
        self.assertEqual(root.name, "root")

        new_status = trace_api.status.Status(
            trace_api.StatusCode.ERROR, "Test description"
        )

        with self.assertLogs(level=WARNING):
            root.set_status(new_status)
        self.assertEqual(root.status.status_code, trace_api.StatusCode.UNSET)

    def test_error_status(self):
        def error_status_test(context):
            with self.assertRaises(AssertionError):
                with context as root:
                    raise AssertionError("unknown")
            self.assertIs(root.status.status_code, StatusCode.ERROR)
            self.assertEqual(
                root.status.description, "AssertionError: unknown"
            )

        error_status_test(
            trace.TracerProvider().get_tracer(__name__).start_span("root")
        )
        error_status_test(
            trace.TracerProvider()
            .get_tracer(__name__)
            .start_as_current_span("root")
        )

    def test_status_cannot_override_ok(self):
        def error_status_test(context):
            with self.assertRaises(AssertionError):
                with context as root:
                    root.set_status(trace_api.status.Status(StatusCode.OK))
                    raise AssertionError("unknown")
            self.assertIs(root.status.status_code, StatusCode.OK)
            self.assertIsNone(root.status.description)

        error_status_test(
            trace.TracerProvider().get_tracer(__name__).start_span("root")
        )
        error_status_test(
            trace.TracerProvider()
            .get_tracer(__name__)
            .start_as_current_span("root")
        )

    def test_status_cannot_set_unset(self):
        def unset_status_test(context):
            with self.assertRaises(AssertionError):
                with context as root:
                    raise AssertionError("unknown")
            root.set_status(trace_api.status.Status(StatusCode.UNSET))
            self.assertIs(root.status.status_code, StatusCode.ERROR)
            self.assertEqual(
                root.status.description, "AssertionError: unknown"
            )

        with self.assertLogs(level=WARNING):
            unset_status_test(
                trace.TracerProvider().get_tracer(__name__).start_span("root")
            )
        with self.assertLogs(level=WARNING):
            unset_status_test(
                trace.TracerProvider()
                .get_tracer(__name__)
                .start_as_current_span("root")
            )

    def test_last_status_wins(self):
        def error_status_test(context):
            with self.assertRaises(AssertionError):
                with context as root:
                    raise AssertionError("unknown")
                root.set_status(trace_api.status.Status(StatusCode.OK))
                self.assertIs(root.status.status_code, StatusCode.OK)
                self.assertIsNone(root.status.description)

        error_status_test(
            trace.TracerProvider().get_tracer(__name__).start_span("root")
        )
        error_status_test(
            trace.TracerProvider()
            .get_tracer(__name__)
            .start_as_current_span("root")
        )

    def test_record_exception_fqn(self):
        span = trace._Span("name", mock.Mock(spec=trace_api.SpanContext))
        exception = DummyError("error")
        exception_type = "tests.trace.test_trace.DummyError"
        span.record_exception(exception)
        exception_event = span.events[0]
        self.assertEqual("exception", exception_event.name)
        self.assertEqual(
            "error", exception_event.attributes["exception.message"]
        )
        self.assertEqual(
            exception_type,
            exception_event.attributes["exception.type"],
        )
        self.assertIn(
            "DummyError: error",
            exception_event.attributes["exception.stacktrace"],
        )

    def test_record_exception(self):
        span = trace._Span("name", mock.Mock(spec=trace_api.SpanContext))
        try:
            raise ValueError("invalid")
        except ValueError as err:
            span.record_exception(err)
        exception_event = span.events[0]
        self.assertEqual("exception", exception_event.name)
        self.assertEqual(
            "invalid", exception_event.attributes["exception.message"]
        )
        self.assertEqual(
            "ValueError", exception_event.attributes["exception.type"]
        )
        self.assertIn(
            "ValueError: invalid",
            exception_event.attributes["exception.stacktrace"],
        )

    def test_record_exception_with_attributes(self):
        span = trace._Span("name", mock.Mock(spec=trace_api.SpanContext))
        try:
            raise RuntimeError("error")
        except RuntimeError as err:
            attributes = {"has_additional_attributes": True}
            span.record_exception(err, attributes)
        exception_event = span.events[0]
        self.assertEqual("exception", exception_event.name)
        self.assertEqual(
            "error", exception_event.attributes["exception.message"]
        )
        self.assertEqual(
            "RuntimeError", exception_event.attributes["exception.type"]
        )
        self.assertEqual(
            "False", exception_event.attributes["exception.escaped"]
        )
        self.assertIn(
            "RuntimeError: error",
            exception_event.attributes["exception.stacktrace"],
        )
        self.assertIn("has_additional_attributes", exception_event.attributes)
        self.assertEqual(
            True, exception_event.attributes["has_additional_attributes"]
        )

    def test_record_exception_escaped(self):
        span = trace._Span("name", mock.Mock(spec=trace_api.SpanContext))
        try:
            raise RuntimeError("error")
        except RuntimeError as err:
            span.record_exception(exception=err, escaped=True)
        exception_event = span.events[0]
        self.assertEqual("exception", exception_event.name)
        self.assertEqual(
            "error", exception_event.attributes["exception.message"]
        )
        self.assertEqual(
            "RuntimeError", exception_event.attributes["exception.type"]
        )
        self.assertIn(
            "RuntimeError: error",
            exception_event.attributes["exception.stacktrace"],
        )
        self.assertEqual(
            "True", exception_event.attributes["exception.escaped"]
        )

    def test_record_exception_with_timestamp(self):
        span = trace._Span("name", mock.Mock(spec=trace_api.SpanContext))
        try:
            raise RuntimeError("error")
        except RuntimeError as err:
            timestamp = 1604238587112021089
            span.record_exception(err, timestamp=timestamp)
        exception_event = span.events[0]
        self.assertEqual("exception", exception_event.name)
        self.assertEqual(
            "error", exception_event.attributes["exception.message"]
        )
        self.assertEqual(
            "RuntimeError", exception_event.attributes["exception.type"]
        )
        self.assertIn(
            "RuntimeError: error",
            exception_event.attributes["exception.stacktrace"],
        )
        self.assertEqual(1604238587112021089, exception_event.timestamp)

    def test_record_exception_with_attributes_and_timestamp(self):
        span = trace._Span("name", mock.Mock(spec=trace_api.SpanContext))
        try:
            raise RuntimeError("error")
        except RuntimeError as err:
            attributes = {"has_additional_attributes": True}
            timestamp = 1604238587112021089
            span.record_exception(err, attributes, timestamp)
        exception_event = span.events[0]
        self.assertEqual("exception", exception_event.name)
        self.assertEqual(
            "error", exception_event.attributes["exception.message"]
        )
        self.assertEqual(
            "RuntimeError", exception_event.attributes["exception.type"]
        )
        self.assertIn(
            "RuntimeError: error",
            exception_event.attributes["exception.stacktrace"],
        )
        self.assertIn("has_additional_attributes", exception_event.attributes)
        self.assertEqual(
            True, exception_event.attributes["has_additional_attributes"]
        )
        self.assertEqual(1604238587112021089, exception_event.timestamp)

    def test_record_exception_context_manager(self):
        span = None
        try:
            with self.tracer.start_as_current_span("span") as span:
                raise RuntimeError("example error")
        except RuntimeError:
            pass
        finally:
            self.assertEqual(len(span.events), 1)
            event = span.events[0]
            self.assertEqual("exception", event.name)
            self.assertEqual(
                "RuntimeError", event.attributes["exception.type"]
            )
            self.assertEqual(
                "example error", event.attributes["exception.message"]
            )

            stacktrace = """in test_record_exception_context_manager
    raise RuntimeError("example error")
RuntimeError: example error"""
            self.assertIn(stacktrace, event.attributes["exception.stacktrace"])

        try:
            with self.tracer.start_as_current_span(
                "span", record_exception=False
            ) as span:
                raise RuntimeError("example error")
        except RuntimeError:
            pass
        finally:
            self.assertEqual(len(span.events), 0)

    def test_record_exception_out_of_scope(self):
        span = trace._Span("name", mock.Mock(spec=trace_api.SpanContext))
        out_of_scope_exception = ValueError("invalid")
        span.record_exception(out_of_scope_exception)
        exception_event = span.events[0]
        self.assertEqual("exception", exception_event.name)
        self.assertEqual(
            "invalid", exception_event.attributes["exception.message"]
        )
        self.assertEqual(
            "ValueError", exception_event.attributes["exception.type"]
        )
        self.assertIn(
            "ValueError: invalid",
            exception_event.attributes["exception.stacktrace"],
        )


def span_event_start_fmt(span_processor_name, span_name):
    return span_processor_name + ":" + span_name + ":start"


def span_event_end_fmt(span_processor_name, span_name):
    return span_processor_name + ":" + span_name + ":end"


class MySpanProcessor(trace.SpanProcessor):
    def __init__(self, name, span_list):
        self.name = name
        self.span_list = span_list

    def on_start(
        self, span: "trace.Span", parent_context: Optional[Context] = None
    ) -> None:
        self.span_list.append(span_event_start_fmt(self.name, span.name))

    def on_end(self, span: "trace.ReadableSpan") -> None:
        self.span_list.append(span_event_end_fmt(self.name, span.name))


class TestSpanProcessor(unittest.TestCase):
    def test_span_processor(self):
        tracer_provider = trace.TracerProvider()
        tracer = tracer_provider.get_tracer(__name__)

        spans_calls_list = []  # filled by MySpanProcessor
        expected_list = []  # filled by hand

        # Span processors are created but not added to the tracer yet
        sp1 = MySpanProcessor("SP1", spans_calls_list)
        sp2 = MySpanProcessor("SP2", spans_calls_list)

        with tracer.start_as_current_span("foo"):
            with tracer.start_as_current_span("bar"):
                with tracer.start_as_current_span("baz"):
                    pass

        # at this point lists must be empty
        self.assertEqual(len(spans_calls_list), 0)

        # add single span processor
        tracer_provider.add_span_processor(sp1)

        with tracer.start_as_current_span("foo"):
            expected_list.append(span_event_start_fmt("SP1", "foo"))

            with tracer.start_as_current_span("bar"):
                expected_list.append(span_event_start_fmt("SP1", "bar"))

                with tracer.start_as_current_span("baz"):
                    expected_list.append(span_event_start_fmt("SP1", "baz"))

                expected_list.append(span_event_end_fmt("SP1", "baz"))

            expected_list.append(span_event_end_fmt("SP1", "bar"))

        expected_list.append(span_event_end_fmt("SP1", "foo"))

        self.assertListEqual(spans_calls_list, expected_list)

        spans_calls_list.clear()
        expected_list.clear()

        # go for multiple span processors
        tracer_provider.add_span_processor(sp2)

        with tracer.start_as_current_span("foo"):
            expected_list.append(span_event_start_fmt("SP1", "foo"))
            expected_list.append(span_event_start_fmt("SP2", "foo"))

            with tracer.start_as_current_span("bar"):
                expected_list.append(span_event_start_fmt("SP1", "bar"))
                expected_list.append(span_event_start_fmt("SP2", "bar"))

                with tracer.start_as_current_span("baz"):
                    expected_list.append(span_event_start_fmt("SP1", "baz"))
                    expected_list.append(span_event_start_fmt("SP2", "baz"))

                expected_list.append(span_event_end_fmt("SP1", "baz"))
                expected_list.append(span_event_end_fmt("SP2", "baz"))

            expected_list.append(span_event_end_fmt("SP1", "bar"))
            expected_list.append(span_event_end_fmt("SP2", "bar"))

        expected_list.append(span_event_end_fmt("SP1", "foo"))
        expected_list.append(span_event_end_fmt("SP2", "foo"))

        # compare if two lists are the same
        self.assertListEqual(spans_calls_list, expected_list)

    def test_add_span_processor_after_span_creation(self):
        tracer_provider = trace.TracerProvider()
        tracer = tracer_provider.get_tracer(__name__)

        spans_calls_list = []  # filled by MySpanProcessor
        expected_list = []  # filled by hand

        # Span processors are created but not added to the tracer yet
        sp = MySpanProcessor("SP1", spans_calls_list)

        with tracer.start_as_current_span("foo"):
            with tracer.start_as_current_span("bar"):
                with tracer.start_as_current_span("baz"):
                    # add span processor after spans have been created
                    tracer_provider.add_span_processor(sp)

                expected_list.append(span_event_end_fmt("SP1", "baz"))

            expected_list.append(span_event_end_fmt("SP1", "bar"))

        expected_list.append(span_event_end_fmt("SP1", "foo"))

        self.assertListEqual(spans_calls_list, expected_list)

    def test_to_json(self):
        context = trace_api.SpanContext(
            trace_id=0x000000000000000000000000DEADBEEF,
            span_id=0x00000000DEADBEF0,
            is_remote=False,
            trace_flags=trace_api.TraceFlags(trace_api.TraceFlags.SAMPLED),
        )
        parent = trace._Span("parent-name", context, resource=Resource({}))
        span = trace._Span(
            "span-name", context, resource=Resource({}), parent=parent.context
        )

        self.assertEqual(
            span.to_json(),
            """{
    "name": "span-name",
    "context": {
        "trace_id": "0x000000000000000000000000deadbeef",
        "span_id": "0x00000000deadbef0",
        "trace_state": "[]"
    },
    "kind": "SpanKind.INTERNAL",
    "parent_id": "0x00000000deadbef0",
    "start_time": null,
    "end_time": null,
    "status": {
        "status_code": "UNSET"
    },
    "attributes": {},
    "events": [],
    "links": [],
    "resource": {
        "attributes": {},
        "schema_url": ""
    }
}""",
        )
        self.assertEqual(
            span.to_json(indent=None),
            '{"name": "span-name", "context": {"trace_id": "0x000000000000000000000000deadbeef", "span_id": "0x00000000deadbef0", "trace_state": "[]"}, "kind": "SpanKind.INTERNAL", "parent_id": "0x00000000deadbef0", "start_time": null, "end_time": null, "status": {"status_code": "UNSET"}, "attributes": {}, "events": [], "links": [], "resource": {"attributes": {}, "schema_url": ""}}',
        )

    def test_attributes_to_json(self):
        context = trace_api.SpanContext(
            trace_id=0x000000000000000000000000DEADBEEF,
            span_id=0x00000000DEADBEF0,
            is_remote=False,
            trace_flags=trace_api.TraceFlags(trace_api.TraceFlags.SAMPLED),
        )
        span = trace._Span("span-name", context, resource=Resource({}))
        span.set_attribute("key", "value")
        span.add_event("event", {"key2": "value2"}, 123)
        date_str = ns_to_iso_str(123)
        self.assertEqual(
            span.to_json(indent=None),
            '{"name": "span-name", "context": {"trace_id": "0x000000000000000000000000deadbeef", "span_id": "0x00000000deadbef0", "trace_state": "[]"}, "kind": "SpanKind.INTERNAL", "parent_id": null, "start_time": null, "end_time": null, "status": {"status_code": "UNSET"}, "attributes": {"key": "value"}, "events": [{"name": "event", "timestamp": "'
            + date_str
            + '", "attributes": {"key2": "value2"}}], "links": [], "resource": {"attributes": {}, "schema_url": ""}}',
        )


class TestSpanLimits(unittest.TestCase):
    # pylint: disable=protected-access

    long_val = "v" * 1000

    def _assert_attr_length(self, attr_val, max_len):
        if isinstance(attr_val, str):
            expected = self.long_val
            if max_len is not None:
                expected = expected[:max_len]
            self.assertEqual(attr_val, expected)

    def test_limits_defaults(self):
        limits = trace.SpanLimits()
        self.assertEqual(
            limits.max_attributes,
            trace._DEFAULT_OTEL_ATTRIBUTE_COUNT_LIMIT,
        )
        self.assertEqual(
            limits.max_span_attributes,
            trace._DEFAULT_OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT,
        )
        self.assertEqual(
            limits.max_event_attributes,
            trace._DEFAULT_OTEL_EVENT_ATTRIBUTE_COUNT_LIMIT,
        )
        self.assertEqual(
            limits.max_link_attributes,
            trace._DEFAULT_OTEL_LINK_ATTRIBUTE_COUNT_LIMIT,
        )
        self.assertEqual(
            limits.max_events, trace._DEFAULT_OTEL_SPAN_EVENT_COUNT_LIMIT
        )
        self.assertEqual(
            limits.max_links, trace._DEFAULT_OTEL_SPAN_LINK_COUNT_LIMIT
        )
        self.assertIsNone(limits.max_attribute_length)
        self.assertIsNone(limits.max_span_attribute_length)

    def test_limits_attribute_length_limits_code(self):
        # global limit unset while span limit is set
        limits = trace.SpanLimits(max_span_attribute_length=22)
        self.assertIsNone(limits.max_attribute_length)
        self.assertEqual(limits.max_span_attribute_length, 22)

        # span limit falls back to global limit when no value is provided
        limits = trace.SpanLimits(max_attribute_length=22)
        self.assertEqual(limits.max_attribute_length, 22)
        self.assertEqual(limits.max_span_attribute_length, 22)

        # global and span limits set to different values
        limits = trace.SpanLimits(
            max_attribute_length=22, max_span_attribute_length=33
        )
        self.assertEqual(limits.max_attribute_length, 22)
        self.assertEqual(limits.max_span_attribute_length, 33)

    def test_limits_values_code(self):
        (
            max_attributes,
            max_span_attributes,
            max_link_attributes,
            max_event_attributes,
            max_events,
            max_links,
            max_attr_length,
            max_span_attr_length,
        ) = (
            randint(0, 10000),
            randint(0, 10000),
            randint(0, 10000),
            randint(0, 10000),
            randint(0, 10000),
            randint(0, 10000),
            randint(0, 10000),
            randint(0, 10000),
        )
        limits = trace.SpanLimits(
            max_events=max_events,
            max_links=max_links,
            max_attributes=max_attributes,
            max_span_attributes=max_span_attributes,
            max_event_attributes=max_event_attributes,
            max_link_attributes=max_link_attributes,
            max_attribute_length=max_attr_length,
            max_span_attribute_length=max_span_attr_length,
        )
        self.assertEqual(limits.max_events, max_events)
        self.assertEqual(limits.max_links, max_links)
        self.assertEqual(limits.max_attributes, max_attributes)
        self.assertEqual(limits.max_span_attributes, max_span_attributes)
        self.assertEqual(limits.max_event_attributes, max_event_attributes)
        self.assertEqual(limits.max_link_attributes, max_link_attributes)
        self.assertEqual(limits.max_attribute_length, max_attr_length)
        self.assertEqual(
            limits.max_span_attribute_length, max_span_attr_length
        )

    def test_limits_values_env(self):
        (
            max_attributes,
            max_span_attributes,
            max_link_attributes,
            max_event_attributes,
            max_events,
            max_links,
            max_attr_length,
            max_span_attr_length,
        ) = (
            randint(0, 10000),
            randint(0, 10000),
            randint(0, 10000),
            randint(0, 10000),
            randint(0, 10000),
            randint(0, 10000),
            randint(0, 10000),
            randint(0, 10000),
        )
        with mock.patch.dict(
            "os.environ",
            {
                OTEL_ATTRIBUTE_COUNT_LIMIT: str(max_attributes),
                OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT: str(max_span_attributes),
                OTEL_EVENT_ATTRIBUTE_COUNT_LIMIT: str(max_event_attributes),
                OTEL_LINK_ATTRIBUTE_COUNT_LIMIT: str(max_link_attributes),
                OTEL_SPAN_EVENT_COUNT_LIMIT: str(max_events),
                OTEL_SPAN_LINK_COUNT_LIMIT: str(max_links),
                OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT: str(max_attr_length),
                OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT: str(
                    max_span_attr_length
                ),
            },
        ):
            limits = trace.SpanLimits()
            self.assertEqual(limits.max_events, max_events)
            self.assertEqual(limits.max_links, max_links)
            self.assertEqual(limits.max_attributes, max_attributes)
            self.assertEqual(limits.max_span_attributes, max_span_attributes)
            self.assertEqual(limits.max_event_attributes, max_event_attributes)
            self.assertEqual(limits.max_link_attributes, max_link_attributes)
            self.assertEqual(limits.max_attribute_length, max_attr_length)
            self.assertEqual(
                limits.max_span_attribute_length, max_span_attr_length
            )

    @mock.patch.dict(
        "os.environ",
        {
            OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT: "13",
            OTEL_SPAN_EVENT_COUNT_LIMIT: "7",
            OTEL_SPAN_LINK_COUNT_LIMIT: "4",
            OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT: "11",
            OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT: "15",
        },
    )
    def test_span_limits_env(self):
        self._test_span_limits(
            new_tracer(),
            max_attrs=13,
            max_events=7,
            max_links=4,
            max_attr_len=11,
            max_span_attr_len=15,
        )

    @mock.patch.dict(
        "os.environ",
        {
            OTEL_ATTRIBUTE_COUNT_LIMIT: "13",
            OTEL_SPAN_EVENT_COUNT_LIMIT: "7",
            OTEL_SPAN_LINK_COUNT_LIMIT: "4",
            OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT: "11",
        },
    )
    def test_span_limits_global_env(self):
        self._test_span_limits(
            new_tracer(),
            max_attrs=13,
            max_events=7,
            max_links=4,
            max_attr_len=11,
            max_span_attr_len=11,
        )

    @mock.patch.dict(
        "os.environ",
        {
            OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT: "10",
            OTEL_SPAN_EVENT_COUNT_LIMIT: "20",
            OTEL_SPAN_LINK_COUNT_LIMIT: "30",
            OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT: "40",
            OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT: "50",
        },
    )
    def test_span_limits_default_to_env(self):
        self._test_span_limits(
            new_tracer(
                span_limits=trace.SpanLimits(
                    max_attributes=None,
                    max_events=None,
                    max_links=None,
                    max_attribute_length=None,
                    max_span_attribute_length=None,
                )
            ),
            max_attrs=10,
            max_events=20,
            max_links=30,
            max_attr_len=40,
            max_span_attr_len=50,
        )

    def test_span_limits_code(self):
        self._test_span_limits(
            new_tracer(
                span_limits=trace.SpanLimits(
                    max_attributes=11,
                    max_events=15,
                    max_links=13,
                    max_attribute_length=9,
                    max_span_attribute_length=25,
                )
            ),
            max_attrs=11,
            max_events=15,
            max_links=13,
            max_attr_len=9,
            max_span_attr_len=25,
        )

    @mock.patch.dict(
        "os.environ",
        {
            OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT: "",
            OTEL_SPAN_EVENT_COUNT_LIMIT: "",
            OTEL_SPAN_LINK_COUNT_LIMIT: "",
            OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT: "",
        },
    )
    def test_span_no_limits_env(self):
        self._test_span_no_limits(new_tracer())

    def test_span_no_limits_code(self):
        self._test_span_no_limits(
            new_tracer(
                span_limits=trace.SpanLimits(
                    max_span_attributes=trace.SpanLimits.UNSET,
                    max_links=trace.SpanLimits.UNSET,
                    max_events=trace.SpanLimits.UNSET,
                    max_attribute_length=trace.SpanLimits.UNSET,
                )
            )
        )

    def test_span_zero_global_limit(self):
        self._test_span_limits(
            new_tracer(
                span_limits=trace.SpanLimits(
                    max_attributes=0,
                    max_events=0,
                    max_links=0,
                )
            ),
            0,
            0,
            0,
            0,
            0,
        )

    def test_span_zero_global_nonzero_model(self):
        self._test_span_limits(
            new_tracer(
                span_limits=trace.SpanLimits(
                    max_attributes=0,
                    max_events=0,
                    max_links=0,
                    max_span_attributes=15,
                    max_span_attribute_length=25,
                )
            ),
            15,
            0,
            0,
            0,
            25,
        )

    def test_span_zero_global_unset_model(self):
        self._test_span_no_limits(
            new_tracer(
                span_limits=trace.SpanLimits(
                    max_attributes=0,
                    max_span_attributes=trace.SpanLimits.UNSET,
                    max_links=trace.SpanLimits.UNSET,
                    max_events=trace.SpanLimits.UNSET,
                    max_attribute_length=trace.SpanLimits.UNSET,
                )
            )
        )

    def test_dropped_attributes(self):
        span = get_span_with_dropped_attributes_events_links()
        self.assertEqual(1, span.dropped_links)
        self.assertEqual(2, span.dropped_attributes)
        self.assertEqual(3, span.dropped_events)
        self.assertEqual(2, span.events[0].dropped_attributes)
        self.assertEqual(2, span.links[0].dropped_attributes)

    def _test_span_limits(
        self,
        tracer,
        max_attrs,
        max_events,
        max_links,
        max_attr_len,
        max_span_attr_len,
    ):
        id_generator = RandomIdGenerator()
        some_links = [
            trace_api.Link(
                trace_api.SpanContext(
                    trace_id=id_generator.generate_trace_id(),
                    span_id=id_generator.generate_span_id(),
                    is_remote=False,
                ),
                attributes={"k": self.long_val},
            )
            for _ in range(100)
        ]

        some_attrs = {
            f"init_attribute_{idx}": self.long_val for idx in range(100)
        }
        with tracer.start_as_current_span(
            "root", links=some_links, attributes=some_attrs
        ) as root:
            self.assertEqual(len(root.links), max_links)
            self.assertEqual(len(root.attributes), max_attrs)
            for idx in range(100):
                root.set_attribute(f"my_str_attribute_{idx}", self.long_val)
                root.set_attribute(
                    f"my_byte_attribute_{idx}", self.long_val.encode()
                )
                root.set_attribute(
                    f"my_int_attribute_{idx}", self.long_val.encode()
                )
                root.add_event(
                    f"my_event_{idx}", attributes={"k": self.long_val}
                )

            self.assertEqual(len(root.attributes), max_attrs)
            self.assertEqual(len(root.events), max_events)

            for link in root.links:
                for attr_val in link.attributes.values():
                    self._assert_attr_length(attr_val, max_attr_len)

            for event in root.events:
                for attr_val in event.attributes.values():
                    self._assert_attr_length(attr_val, max_attr_len)

            for attr_val in root.attributes.values():
                self._assert_attr_length(attr_val, max_span_attr_len)

    def _test_span_no_limits(self, tracer):
        num_links = int(trace._DEFAULT_OTEL_SPAN_LINK_COUNT_LIMIT) + randint(
            1, 100
        )

        id_generator = RandomIdGenerator()
        some_links = [
            trace_api.Link(
                trace_api.SpanContext(
                    trace_id=id_generator.generate_trace_id(),
                    span_id=id_generator.generate_span_id(),
                    is_remote=False,
                )
            )
            for _ in range(num_links)
        ]
        with tracer.start_as_current_span("root", links=some_links) as root:
            self.assertEqual(len(root.links), num_links)

        num_events = int(trace._DEFAULT_OTEL_SPAN_EVENT_COUNT_LIMIT) + randint(
            1, 100
        )
        with tracer.start_as_current_span("root") as root:
            for idx in range(num_events):
                root.add_event(
                    f"my_event_{idx}", attributes={"k": self.long_val}
                )

            self.assertEqual(len(root.events), num_events)

        num_attributes = int(
            trace._DEFAULT_OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT
        ) + randint(1, 100)
        with tracer.start_as_current_span("root") as root:
            for idx in range(num_attributes):
                root.set_attribute(f"my_attribute_{idx}", self.long_val)

            self.assertEqual(len(root.attributes), num_attributes)
            for attr_val in root.attributes.values():
                self.assertEqual(attr_val, self.long_val)


class TestTraceFlags(unittest.TestCase):
    def test_constant_default(self):
        self.assertEqual(trace_api.TraceFlags.DEFAULT, 0)

    def test_constant_sampled(self):
        self.assertEqual(trace_api.TraceFlags.SAMPLED, 1)

    def test_get_default(self):
        self.assertEqual(
            trace_api.TraceFlags.get_default(), trace_api.TraceFlags.DEFAULT
        )

    def test_sampled_true(self):
        self.assertTrue(trace_api.TraceFlags(0xF1).sampled)

    def test_sampled_false(self):
        self.assertFalse(trace_api.TraceFlags(0xF0).sampled)

    def test_constant_default_trace_options(self):
        self.assertEqual(
            trace_api.DEFAULT_TRACE_OPTIONS, trace_api.TraceFlags.DEFAULT
        )


class TestParentChildSpanException(unittest.TestCase):
    def test_parent_child_span_exception(self):
        """
        Tests that a parent span has its status set to ERROR when a child span
        raises an exception even when the child span has its
        ``record_exception`` and ``set_status_on_exception`` attributes
        set to ``False``.
        """

        set_tracer_provider(TracerProvider())
        tracer = get_tracer(__name__)

        exception = Exception("exception")

        exception_type = exception.__class__.__name__
        exception_message = exception.args[0]

        try:
            with tracer.start_as_current_span(
                "parent",
            ) as parent_span:
                with tracer.start_as_current_span(
                    "child",
                    record_exception=False,
                    set_status_on_exception=False,
                ) as child_span:
                    raise exception

        except Exception:  # pylint: disable=broad-exception-caught
            pass

        self.assertTrue(child_span.status.is_ok)
        self.assertIsNone(child_span.status.description)
        self.assertTupleEqual(child_span.events, ())

        self.assertFalse(parent_span.status.is_ok)
        self.assertEqual(
            parent_span.status.description,
            f"{exception_type}: {exception_message}",
        )
        self.assertEqual(
            parent_span.events[0].attributes["exception.type"], exception_type
        )
        self.assertEqual(
            parent_span.events[0].attributes["exception.message"],
            exception_message,
        )

    def test_child_parent_span_exception(self):
        """
        Tests that a child span does not have its status set to ERROR when a
        parent span raises an exception and the parent span has its
        ``record_exception`` and ``set_status_on_exception`` attributes
        set to ``False``.
        """

        set_tracer_provider(TracerProvider())
        tracer = get_tracer(__name__)

        exception = Exception("exception")

        try:
            with tracer.start_as_current_span(
                "parent",
                record_exception=False,
                set_status_on_exception=False,
            ) as parent_span:
                with tracer.start_as_current_span(
                    "child",
                ) as child_span:
                    pass
                raise exception

        except Exception:  # pylint: disable=broad-exception-caught
            pass

        self.assertTrue(child_span.status.is_ok)
        self.assertIsNone(child_span.status.description)
        self.assertTupleEqual(child_span.events, ())

        self.assertTrue(parent_span.status.is_ok)
        self.assertIsNone(parent_span.status.description)
        self.assertTupleEqual(parent_span.events, ())


# pylint: disable=protected-access
class TestTracerProvider(unittest.TestCase):
    @patch("opentelemetry.sdk.trace.sampling._get_from_env_or_default")
    @patch.object(Resource, "create")
    def test_tracer_provider_init_default(self, resource_patch, sample_patch):
        tracer_provider = trace.TracerProvider()
        self.assertTrue(
            isinstance(tracer_provider.id_generator, RandomIdGenerator)
        )
        resource_patch.assert_called_once()
        self.assertIsNotNone(tracer_provider._resource)
        sample_patch.assert_called_once()
        self.assertIsNotNone(tracer_provider._span_limits)
        self.assertIsNotNone(tracer_provider._atexit_handler)


class TestRandomIdGenerator(unittest.TestCase):
    _TRACE_ID_MAX_VALUE = 2**128 - 1
    _SPAN_ID_MAX_VALUE = 2**64 - 1

    @patch(
        "random.getrandbits",
        side_effect=[trace_api.INVALID_SPAN_ID, 0x00000000DEADBEF0],
    )
    def test_generate_span_id_avoids_invalid(self, mock_getrandbits):
        generator = RandomIdGenerator()
        span_id = generator.generate_span_id()

        self.assertNotEqual(span_id, trace_api.INVALID_SPAN_ID)
        mock_getrandbits.assert_any_call(64)
        self.assertEqual(mock_getrandbits.call_count, 2)

    @patch(
        "random.getrandbits",
        side_effect=[
            trace_api.INVALID_TRACE_ID,
            0x000000000000000000000000DEADBEEF,
        ],
    )
    def test_generate_trace_id_avoids_invalid(self, mock_getrandbits):
        generator = RandomIdGenerator()
        trace_id = generator.generate_trace_id()

        self.assertNotEqual(trace_id, trace_api.INVALID_TRACE_ID)
        mock_getrandbits.assert_any_call(128)
        self.assertEqual(mock_getrandbits.call_count, 2)
