# Copyright 2019, OpenTelemetry Authors
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

import shutil
import subprocess
import unittest
from unittest import mock

from opentelemetry import trace as trace_api
from opentelemetry.sdk import trace
from opentelemetry.trace import sampling
from opentelemetry.trace.status import StatusCanonicalCode
from opentelemetry.util import time_ns


def new_tracer() -> trace_api.Tracer:
    return trace.TracerSource().get_tracer(__name__)


class TestTracer(unittest.TestCase):
    def test_extends_api(self):
        tracer = new_tracer()
        self.assertIsInstance(tracer, trace.Tracer)
        self.assertIsInstance(tracer, trace_api.Tracer)

    def test_shutdown(self):
        tracer_source = trace.TracerSource()

        mock_processor1 = mock.Mock(spec=trace.SpanProcessor)
        tracer_source.add_span_processor(mock_processor1)

        mock_processor2 = mock.Mock(spec=trace.SpanProcessor)
        tracer_source.add_span_processor(mock_processor2)

        tracer_source.shutdown()

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

tracer_source = trace.TracerSource({tracer_parameters})
tracer_source.add_span_processor(mock_processor)

{tracer_shutdown}
"""

        def run_general_code(shutdown_on_exit, explicit_shutdown):
            tracer_parameters = ""
            tracer_shutdown = ""

            if not shutdown_on_exit:
                tracer_parameters = "shutdown_on_exit=False"

            if explicit_shutdown:
                tracer_shutdown = "tracer_source.shutdown()"

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
        # called explicitely
        out = run_general_code(True, True)
        self.assertTrue(out.startswith(b"1"))

        # test shutdown_on_exit=False
        out = run_general_code(False, False)
        self.assertTrue(out.startswith(b"0"))


class TestTracerSampling(unittest.TestCase):
    def test_default_sampler(self):
        tracer = new_tracer()

        # Check that the default tracer creates real spans via the default
        # sampler
        root_span = tracer.start_span(name="root span", parent=None)
        self.assertIsInstance(root_span, trace.Span)
        child_span = tracer.start_span(name="child span", parent=root_span)
        self.assertIsInstance(child_span, trace.Span)

    def test_sampler_no_sampling(self):
        tracer_source = trace.TracerSource(sampling.ALWAYS_OFF)
        tracer = tracer_source.get_tracer(__name__)

        # Check that the default tracer creates no-op spans if the sampler
        # decides not to sampler
        root_span = tracer.start_span(name="root span", parent=None)
        self.assertIsInstance(root_span, trace_api.DefaultSpan)
        child_span = tracer.start_span(name="child span", parent=root_span)
        self.assertIsInstance(child_span, trace_api.DefaultSpan)


class TestSpanCreation(unittest.TestCase):
    def test_start_span_invalid_spancontext(self):
        """If an invalid span context is passed as the parent, the created
        span should use a new span id.

        Invalid span contexts should also not be added as a parent. This
        eliminates redundant error handling logic in exporters.
        """
        tracer = new_tracer()
        new_span = tracer.start_span(
            "root", parent=trace_api.INVALID_SPAN_CONTEXT
        )
        self.assertTrue(new_span.context.is_valid())
        self.assertIsNone(new_span.parent)

    def test_instrumentation_info(self):
        tracer_source = trace.TracerSource()
        tracer1 = tracer_source.get_tracer("instr1")
        tracer2 = tracer_source.get_tracer("instr2", "1.3b3")
        span1 = tracer1.start_span("s1")
        span2 = tracer2.start_span("s2")
        self.assertEqual(
            span1.instrumentation_info, trace.InstrumentationInfo("instr1", "")
        )
        self.assertEqual(
            span2.instrumentation_info,
            trace.InstrumentationInfo("instr2", "1.3b3"),
        )

        self.assertEqual(span2.instrumentation_info.version, "1.3b3")
        self.assertEqual(span2.instrumentation_info.name, "instr2")

        self.assertLess(
            span1.instrumentation_info, span2.instrumentation_info
        )  # Check sortability.

    def test_invalid_instrumentation_info(self):
        tracer_source = trace.TracerSource()
        tracer1 = tracer_source.get_tracer("")
        tracer2 = tracer_source.get_tracer(None)
        self.assertEqual(
            tracer1.instrumentation_info, tracer2.instrumentation_info
        )
        self.assertIsInstance(
            tracer1.instrumentation_info, trace.InstrumentationInfo
        )
        span1 = tracer1.start_span("foo")
        self.assertTrue(span1.is_recording_events())
        self.assertEqual(tracer1.instrumentation_info.version, "")
        self.assertEqual(
            tracer1.instrumentation_info.name, "ERROR:MISSING MODULE NAME"
        )

    def test_span_processor_for_source(self):
        tracer_source = trace.TracerSource()
        tracer1 = tracer_source.get_tracer("instr1")
        tracer2 = tracer_source.get_tracer("instr2", "1.3b3")
        span1 = tracer1.start_span("s1")
        span2 = tracer2.start_span("s2")

        # pylint:disable=protected-access
        self.assertIs(
            span1.span_processor, tracer_source._active_span_processor
        )
        self.assertIs(
            span2.span_processor, tracer_source._active_span_processor
        )

    def test_start_span_implicit(self):
        tracer = new_tracer()

        self.assertIsNone(tracer.get_current_span())

        root = tracer.start_span("root")
        self.assertIsNotNone(root.start_time)
        self.assertIsNone(root.end_time)
        self.assertEqual(root.kind, trace_api.SpanKind.INTERNAL)

        with tracer.use_span(root, True):
            self.assertIs(tracer.get_current_span(), root)

            with tracer.start_span(
                "child", kind=trace_api.SpanKind.CLIENT
            ) as child:
                self.assertIs(child.parent, root)
                self.assertEqual(child.kind, trace_api.SpanKind.CLIENT)

                self.assertIsNotNone(child.start_time)
                self.assertIsNone(child.end_time)

                # The new child span should inherit the parent's context but
                # get a new span ID.
                root_context = root.get_context()
                child_context = child.get_context()
                self.assertEqual(root_context.trace_id, child_context.trace_id)
                self.assertNotEqual(
                    root_context.span_id, child_context.span_id
                )
                self.assertEqual(
                    root_context.trace_state, child_context.trace_state
                )
                self.assertEqual(
                    root_context.trace_options, child_context.trace_options
                )

                # Verify start_span() did not set the current span.
                self.assertIs(tracer.get_current_span(), root)

            self.assertIsNotNone(child.end_time)

        self.assertIsNone(tracer.get_current_span())
        self.assertIsNotNone(root.end_time)

    def test_start_span_explicit(self):
        tracer = new_tracer()

        other_parent = trace_api.SpanContext(
            trace_id=0x000000000000000000000000DEADBEEF,
            span_id=0x00000000DEADBEF0,
        )

        self.assertIsNone(tracer.get_current_span())

        root = tracer.start_span("root")
        self.assertIsNotNone(root.start_time)
        self.assertIsNone(root.end_time)

        # Test with the implicit root span
        with tracer.use_span(root, True):
            self.assertIs(tracer.get_current_span(), root)

            with tracer.start_span("stepchild", other_parent) as child:
                # The child's parent should be the one passed in,
                # not the current span.
                self.assertNotEqual(child.parent, root)
                self.assertIs(child.parent, other_parent)

                self.assertIsNotNone(child.start_time)
                self.assertIsNone(child.end_time)

                # The child should inherit its context from the explicit
                # parent, not the current span.
                child_context = child.get_context()
                self.assertEqual(other_parent.trace_id, child_context.trace_id)
                self.assertNotEqual(
                    other_parent.span_id, child_context.span_id
                )
                self.assertEqual(
                    other_parent.trace_state, child_context.trace_state
                )
                self.assertEqual(
                    other_parent.trace_options, child_context.trace_options
                )

                # Verify start_span() did not set the current span.
                self.assertIs(tracer.get_current_span(), root)

            # Verify ending the child did not set the current span.
            self.assertIs(tracer.get_current_span(), root)
            self.assertIsNotNone(child.end_time)

    def test_start_as_current_span_implicit(self):
        tracer = new_tracer()

        self.assertIsNone(tracer.get_current_span())

        with tracer.start_as_current_span("root") as root:
            self.assertIs(tracer.get_current_span(), root)

            with tracer.start_as_current_span("child") as child:
                self.assertIs(tracer.get_current_span(), child)
                self.assertIs(child.parent, root)

            # After exiting the child's scope the parent should become the
            # current span again.
            self.assertIs(tracer.get_current_span(), root)
            self.assertIsNotNone(child.end_time)

        self.assertIsNone(tracer.get_current_span())
        self.assertIsNotNone(root.end_time)

    def test_start_as_current_span_explicit(self):
        tracer = new_tracer()

        other_parent = trace_api.SpanContext(
            trace_id=0x000000000000000000000000DEADBEEF,
            span_id=0x00000000DEADBEF0,
        )

        self.assertIsNone(tracer.get_current_span())

        # Test with the implicit root span
        with tracer.start_as_current_span("root") as root:
            self.assertIs(tracer.get_current_span(), root)

            self.assertIsNotNone(root.start_time)
            self.assertIsNone(root.end_time)

            with tracer.start_as_current_span(
                "stepchild", other_parent
            ) as child:
                # The child should become the current span as usual, but its
                # parent should be the one passed in, not the
                # previously-current span.
                self.assertIs(tracer.get_current_span(), child)
                self.assertNotEqual(child.parent, root)
                self.assertIs(child.parent, other_parent)

            # After exiting the child's scope the last span on the stack should
            # become current, not the child's parent.
            self.assertNotEqual(tracer.get_current_span(), other_parent)
            self.assertIs(tracer.get_current_span(), root)
            self.assertIsNotNone(child.end_time)


class TestSpan(unittest.TestCase):
    def setUp(self):
        self.tracer = new_tracer()

    def test_basic_span(self):
        span = trace.Span("name", mock.Mock(spec=trace_api.SpanContext))
        self.assertEqual(span.name, "name")

    def test_attributes(self):
        with self.tracer.start_as_current_span("root") as root:
            root.set_attribute("component", "http")
            root.set_attribute("http.method", "GET")
            root.set_attribute(
                "http.url", "https://example.com:779/path/12/?q=d#123"
            )
            root.set_attribute("http.status_code", 200)
            root.set_attribute("http.status_text", "OK")
            root.set_attribute("misc.pi", 3.14)

            # Setting an attribute with the same key as an existing attribute
            # SHOULD overwrite the existing attribute's value.
            root.set_attribute("attr-key", "attr-value1")
            root.set_attribute("attr-key", "attr-value2")

            root.set_attribute("empty-list", [])
            root.set_attribute("list-of-bools", [True, True, False])
            root.set_attribute("list-of-numerics", [123, 3.14, 0])

            self.assertEqual(len(root.attributes), 10)
            self.assertEqual(root.attributes["component"], "http")
            self.assertEqual(root.attributes["http.method"], "GET")
            self.assertEqual(
                root.attributes["http.url"],
                "https://example.com:779/path/12/?q=d#123",
            )
            self.assertEqual(root.attributes["http.status_code"], 200)
            self.assertEqual(root.attributes["http.status_text"], "OK")
            self.assertEqual(root.attributes["misc.pi"], 3.14)
            self.assertEqual(root.attributes["attr-key"], "attr-value2")
            self.assertEqual(root.attributes["empty-list"], [])
            self.assertEqual(
                root.attributes["list-of-bools"], [True, True, False]
            )
            self.assertEqual(
                root.attributes["list-of-numerics"], [123, 3.14, 0]
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
            root.set_attribute("non-primitive-data-type", dict())
            root.set_attribute(
                "list-of-mixed-data-types-numeric-first",
                [123, False, "string"],
            )
            root.set_attribute(
                "list-of-mixed-data-types-non-numeric-first",
                [False, 123, "string"],
            )
            root.set_attribute(
                "list-with-non-primitive-data-type", [dict(), 123]
            )

            self.assertEqual(len(root.attributes), 0)

    def test_check_sequence_helper(self):
        # pylint: disable=protected-access
        self.assertEqual(
            trace.Span._check_attribute_value_sequence([1, 2, 3.4, "ss", 4]), "different type"
        )
        self.assertEqual(
            trace.Span._check_attribute_value_sequence([dict(), 1, 2, 3.4, 4]), "invalid type"
        )
        self.assertEqual(
            trace.Span._check_attribute_value_sequence(["sw", "lf", 3.4, "ss"]),
            "different type",
        )
        self.assertIsNone(trace.Span._check_attribute_value_sequence([1, 2, 3.4, 5]))
        self.assertIsNone(trace.Span._check_attribute_value_sequence(["ss", "dw", "fw"]))

    def test_sampling_attributes(self):
        decision_attributes = {
            "sampler-attr": "sample-val",
            "attr-in-both": "decision-attr",
        }
        tracer_source = trace.TracerSource(
            sampling.StaticSampler(
                sampling.Decision(sampled=True, attributes=decision_attributes)
            )
        )

        self.tracer = tracer_source.get_tracer(__name__)

        with self.tracer.start_as_current_span("root2") as root:
            self.assertEqual(len(root.attributes), 2)
            self.assertEqual(root.attributes["sampler-attr"], "sample-val")
            self.assertEqual(root.attributes["attr-in-both"], "decision-attr")

        attributes = {
            "attr-key": "val",
            "attr-key2": "val2",
            "attr-in-both": "span-attr",
        }
        with self.tracer.start_as_current_span(
            "root2", attributes=attributes
        ) as root:
            self.assertEqual(len(root.attributes), 4)
            self.assertEqual(root.attributes["attr-key"], "val")
            self.assertEqual(root.attributes["attr-key2"], "val2")
            self.assertEqual(root.attributes["sampler-attr"], "sample-val")
            self.assertEqual(root.attributes["attr-in-both"], "decision-attr")

    def test_events(self):
        self.assertIsNone(self.tracer.get_current_span())

        with self.tracer.start_as_current_span("root") as root:
            # only event name
            root.add_event("event0")

            # event name and attributes
            now = time_ns()
            root.add_event("event1", {"name": "pluto"})

            # event name, attributes and timestamp
            now = time_ns()
            root.add_event("event2", {"name": "birthday"}, now)

            # lazy event
            root.add_lazy_event(
                trace_api.Event("event3", {"name": "hello"}, now)
            )

            self.assertEqual(len(root.events), 4)

            self.assertEqual(root.events[0].name, "event0")
            self.assertEqual(root.events[0].attributes, {})

            self.assertEqual(root.events[1].name, "event1")
            self.assertEqual(root.events[1].attributes, {"name": "pluto"})

            self.assertEqual(root.events[2].name, "event2")
            self.assertEqual(root.events[2].attributes, {"name": "birthday"})
            self.assertEqual(root.events[2].timestamp, now)

            self.assertEqual(root.events[3].name, "event3")
            self.assertEqual(root.events[3].attributes, {"name": "hello"})
            self.assertEqual(root.events[3].timestamp, now)

    def test_links(self):
        other_context1 = trace_api.SpanContext(
            trace_id=trace.generate_trace_id(),
            span_id=trace.generate_span_id(),
        )
        other_context2 = trace_api.SpanContext(
            trace_id=trace.generate_trace_id(),
            span_id=trace.generate_span_id(),
        )
        other_context3 = trace_api.SpanContext(
            trace_id=trace.generate_trace_id(),
            span_id=trace.generate_span_id(),
        )
        links = [
            trace_api.Link(other_context1),
            trace_api.Link(other_context2, {"name": "neighbor"}),
            trace_api.Link(other_context3, {"component": "http"}),
        ]
        with self.tracer.start_as_current_span("root", links=links) as root:

            self.assertEqual(len(root.links), 3)
            self.assertEqual(
                root.links[0].context.trace_id, other_context1.trace_id
            )
            self.assertEqual(
                root.links[0].context.span_id, other_context1.span_id
            )
            self.assertEqual(root.links[0].attributes, {})
            self.assertEqual(
                root.links[1].context.trace_id, other_context2.trace_id
            )
            self.assertEqual(
                root.links[1].context.span_id, other_context2.span_id
            )
            self.assertEqual(root.links[1].attributes, {"name": "neighbor"})
            self.assertEqual(
                root.links[2].context.span_id, other_context3.span_id
            )
            self.assertEqual(root.links[2].attributes, {"component": "http"})

    def test_update_name(self):
        with self.tracer.start_as_current_span("root") as root:
            # name
            root.update_name("toor")
            self.assertEqual(root.name, "toor")

    def test_start_span(self):
        """Start twice, end a not started"""
        span = trace.Span("name", mock.Mock(spec=trace_api.SpanContext))

        # end not started span
        self.assertRaises(RuntimeError, span.end)

        span.start()
        start_time = span.start_time
        span.start()
        self.assertEqual(start_time, span.start_time)

        self.assertIs(span.status, None)

        # status
        new_status = trace_api.status.Status(
            trace_api.status.StatusCanonicalCode.CANCELLED, "Test description"
        )
        span.set_status(new_status)
        self.assertIs(
            span.status.canonical_code,
            trace_api.status.StatusCanonicalCode.CANCELLED,
        )
        self.assertIs(span.status.description, "Test description")

    def test_span_override_start_and_end_time(self):
        """Span sending custom start_time and end_time values"""
        span = trace.Span("name", mock.Mock(spec=trace_api.SpanContext))
        start_time = 123
        span.start(start_time)
        self.assertEqual(start_time, span.start_time)
        end_time = 456
        span.end(end_time)
        self.assertEqual(end_time, span.end_time)

    def test_ended_span(self):
        """"Events, attributes are not allowed after span is ended"""

        with self.tracer.start_as_current_span("root") as root:
            # everything should be empty at the beginning
            self.assertEqual(len(root.attributes), 0)
            self.assertEqual(len(root.events), 0)
            self.assertEqual(len(root.links), 0)

            # call end first time
            root.end()
            end_time0 = root.end_time

            # call it a second time
            root.end()
            # end time shouldn't be changed
            self.assertEqual(end_time0, root.end_time)

            root.set_attribute("component", "http")
            self.assertEqual(len(root.attributes), 0)

            root.add_event("event1")
            self.assertEqual(len(root.events), 0)

            root.update_name("xxx")
            self.assertEqual(root.name, "root")

            new_status = trace_api.status.Status(
                trace_api.status.StatusCanonicalCode.CANCELLED,
                "Test description",
            )
            root.set_status(new_status)
            self.assertIs(root.status, None)

    def test_error_status(self):
        try:
            with trace.TracerSource().get_tracer(__name__).start_span(
                "root"
            ) as root:
                raise Exception("unknown")
        except Exception:  # pylint: disable=broad-except
            pass

        self.assertIs(root.status.canonical_code, StatusCanonicalCode.UNKNOWN)
        self.assertEqual(root.status.description, "Exception: unknown")


def span_event_start_fmt(span_processor_name, span_name):
    return span_processor_name + ":" + span_name + ":start"


def span_event_end_fmt(span_processor_name, span_name):
    return span_processor_name + ":" + span_name + ":end"


class MySpanProcessor(trace.SpanProcessor):
    def __init__(self, name, span_list):
        self.name = name
        self.span_list = span_list

    def on_start(self, span: "trace.Span") -> None:
        self.span_list.append(span_event_start_fmt(self.name, span.name))

    def on_end(self, span: "trace.Span") -> None:
        self.span_list.append(span_event_end_fmt(self.name, span.name))


class TestSpanProcessor(unittest.TestCase):
    def test_span_processor(self):
        tracer_source = trace.TracerSource()
        tracer = tracer_source.get_tracer(__name__)

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
        tracer_source.add_span_processor(sp1)

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
        tracer_source.add_span_processor(sp2)

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
        tracer_source = trace.TracerSource()
        tracer = tracer_source.get_tracer(__name__)

        spans_calls_list = []  # filled by MySpanProcessor
        expected_list = []  # filled by hand

        # Span processors are created but not added to the tracer yet
        sp = MySpanProcessor("SP1", spans_calls_list)

        with tracer.start_as_current_span("foo"):
            with tracer.start_as_current_span("bar"):
                with tracer.start_as_current_span("baz"):
                    # add span processor after spans have been created
                    tracer_source.add_span_processor(sp)

                expected_list.append(span_event_end_fmt("SP1", "baz"))

            expected_list.append(span_event_end_fmt("SP1", "bar"))

        expected_list.append(span_event_end_fmt("SP1", "foo"))

        self.assertListEqual(spans_calls_list, expected_list)
