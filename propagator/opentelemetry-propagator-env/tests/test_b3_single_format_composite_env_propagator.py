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

import os
import re
import unittest
from unittest import mock

import opentelemetry
from opentelemetry.propagators.textmap import DefaultGetter, DefaultSetter
from opentelemetry.propagators.b3 import B3SingleFormat
from opentelemetry.propagators.env.composite_propagator import CompositeEnvPropagator
from tests.utils import create_valid_context_with_baggage, create_valid_context_with_baggage2, create_dummy_context_with_parent_span
from tests.utils import *

getter = DefaultGetter()
class TestB3CompositeEnvPropagator(unittest.TestCase):
    def setUp(self):
        self.mock_carrier = {}
        self.b3_composite_env_propagator_object = CompositeEnvPropagator([B3SingleFormat()])
        self.composite_env_propagator_None_obj = CompositeEnvPropagator(None)
        self.b3_object = B3SingleFormat()

    # Test cases for inject_to_carrier

    def test_inject_to_carrier_when_valid_context_with_baggage_attached(self):
        dummy_context = create_valid_context_with_baggage()
        token = opentelemetry.context.attach(dummy_context)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        self.mock_carrier = self.b3_composite_env_propagator_object.inject_to_carrier()
        opentelemetry.context.detach(token)
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertEqual(self.mock_carrier.get("b3") , str(traceid)+'-'+str(spanid)+'-'+str(sampled))
        self.assertIsNone(self.mock_carrier.get("baggage"))

    def test_inject_to_carrier_when_valid_context_with_baggage_passed_as_param(self):
        dummy_context = create_valid_context_with_baggage()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        self.mock_carrier = self.b3_composite_env_propagator_object.inject_to_carrier(context = dummy_context)
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertEqual(self.mock_carrier.get("b3") , str(traceid)+'-'+str(spanid)+'-'+str(sampled))
        self.assertIsNone( self.mock_carrier.get("baggage"))

    def test_inject_to_carrier_when_valid_context_passed_as_param_without_baggage(self):
        dummy_context = create_dummy_context_with_parent_span()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        self.mock_carrier = self.b3_composite_env_propagator_object.inject_to_carrier(context = dummy_context)
        self.assertIsNone( self.mock_carrier.get("traceparent"))
        self.assertEqual(self.mock_carrier.get("b3") , str(traceid)+'-'+str(spanid)+'-'+str(sampled)+'-'+str(parentspanid))
        self.assertIsNone( self.mock_carrier.get("baggage"))

    def test_inject_to_carrier_when_context_attached_and_context_passed_with_baggage_are_different(self):
        dummy_context = create_valid_context_with_baggage()
        token = opentelemetry.context.attach(dummy_context)
        context_passed = create_valid_context_with_baggage2()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        traceid2, spanid2, sampled2, parentspanid2, tracestate2 = get_details_from_context(context_passed)
        self.mock_carrier = self.b3_composite_env_propagator_object.inject_to_carrier(context_passed)
        opentelemetry.context.detach(token)
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertEqual(self.mock_carrier.get("b3") , str(traceid2)+'-'+str(spanid2)+'-'+str(sampled2))
        self.assertNotEqual(self.mock_carrier.get("b3") , str(traceid)+'-'+str(spanid)+'-'+str(sampled))
        self.assertIsNone(self.mock_carrier.get("baggage"))

    def test_inject_to_carrier_when_invalid_context_passed(self):
        dummy_context = create_invalid_context_with_baggage()
        self.mock_carrier = self.b3_composite_env_propagator_object.inject_to_carrier(context = dummy_context)
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertIsNone(self.mock_carrier.get("b3"))
        self.assertIsNone(self.mock_carrier.get("baggage"))

    def test_inject_to_carrier_when_invalid_context_attached(self):
        current_context = create_invalid_context_with_baggage()
        token = opentelemetry.context.attach(current_context)
        self.mock_carrier = self.b3_composite_env_propagator_object.inject_to_carrier()
        opentelemetry.context.detach(token)
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertIsNone(self.mock_carrier.get("b3"))
        self.assertIsNone(self.mock_carrier.get("baggage"))

    ## Test cases for inject

    def test_inject_b3format_when_valid_context_with_parent_span_id_attached(self):
        test_context = create_dummy_context_with_parent_span()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(test_context)
        token = opentelemetry.context.attach(test_context)
        self.b3_composite_env_propagator_object.inject(carrier = self.mock_carrier, setter = DefaultSetter())
        opentelemetry.context.detach(token)
        if parent_span_id is not None:
            self.assertEqual(self.mock_carrier.get("b3") , str(trace_id)+"-"+str(span_id)+"-"+str(int(sampled_flag))+"-"+str(parent_span_id))

    def test_inject_b3format_when_valid_context_without_parent_span_id_attached(self):
        test_context = create_dummy_context()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(test_context)
        token = opentelemetry.context.attach(test_context)
        self.b3_composite_env_propagator_object.inject(carrier = self.mock_carrier, setter = DefaultSetter())
        opentelemetry.context.detach(token)
        self.assertEqual(self.mock_carrier.get("b3") , str(trace_id)+"-"+str(span_id)+"-"+str(int(sampled_flag)))

    def test_inject_b3format_when_valid_context_with_parent_span_id_passed_as_param(self):
        test_context = create_dummy_context_with_parent_span()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(test_context)
        self.b3_composite_env_propagator_object.inject(carrier = self.mock_carrier, context = test_context, setter = DefaultSetter())
        if parent_span_id is not None:
            self.assertEqual(self.mock_carrier.get("b3") , str(trace_id)+"-"+str(span_id)+"-"+str(int(sampled_flag))+"-"+str(parent_span_id))

    def test_inject_b3format_when_valid_context_without_parent_span_id_passed_as_param(self):
        test_context = create_dummy_context()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(test_context)
        self.b3_composite_env_propagator_object.inject(carrier = self.mock_carrier, context = test_context, setter = DefaultSetter())
        self.assertEqual(self.mock_carrier.get("b3") , str(trace_id)+"-"+str(span_id)+"-"+str(int(sampled_flag)))


    def test_inject_b3format_when_invalid_context_attached(self):
        test_context = create_invalid_context()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(test_context)
        token = opentelemetry.context.attach(test_context)
        self.b3_composite_env_propagator_object.inject(carrier = self.mock_carrier, setter = DefaultSetter())
        opentelemetry.context.detach(token)
        self.assertIsNone(self.mock_carrier.get("b3"))

    def test_inject_b3format_when_invalid_context_passed_as_param(self):
        test_context = create_invalid_context()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(test_context)
        self.b3_composite_env_propagator_object.inject(carrier = self.mock_carrier, context = test_context, setter = DefaultSetter())
        self.assertIsNone(self.mock_carrier.get("b3"))

    def test_inject_b3format_when_invalid_context_with_baggage_attached(self):
        test_context = create_invalid_context_with_baggage()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(test_context)
        token = opentelemetry.context.attach(test_context)
        self.b3_composite_env_propagator_object.inject(carrier = self.mock_carrier, setter = DefaultSetter())
        opentelemetry.context.detach(token)
        self.assertIsNone(self.mock_carrier.get("b3"))
        self.assertIsNone(self.mock_carrier.get("baggage"))

    def test_inject_b3format_when_invalid_context_with_baggage_passed_as_param(self):
        test_context = create_invalid_context_with_baggage()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(test_context)
        self.b3_composite_env_propagator_object.inject(carrier = self.mock_carrier, context = test_context, setter = DefaultSetter())
        self.assertIsNone(self.mock_carrier.get("b3"))
        self.assertIsNone(self.mock_carrier.get("baggage") )

    def test_inject_when_context_attached_and_context_passed_as_param_are_different(self):
        dummy_context = create_dummy_context2()
        token = opentelemetry.context.attach(dummy_context)
        context_passed = create_dummy_context_with_parent_span()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(context_passed)
        traceid2, spanid2, sampled2, parentspanid2, tracestate2 = get_details_from_context(dummy_context)
        self.b3_composite_env_propagator_object.inject(carrier = self.mock_carrier, context = context_passed, setter = DefaultSetter())
        opentelemetry.context.detach(token)
        self.assertEqual(self.mock_carrier.get("b3") , str(traceid)+'-'+str(spanid)+'-'+str(sampled)+'-'+str(parentspanid))
        self.assertNotEqual(self.mock_carrier.get("b3") , str(traceid2)+'-'+str(spanid2)+'-'+str(sampled2))

    # Test cases for extract

    @mock.patch.dict(os.environ, {'b3':'8128c50fd8653b5d98fea4de58eca772-136eec09c948be26-1-e28bf981e15deb7f'})
    def test_extract_b3format_valid_format_with_parent_span_present(self):
        extracted_context = self.b3_composite_env_propagator_object.extract(getter = getter, carrier = os.environ)
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(extracted_context)
        self.assertEqual(trace_id , "8128c50fd8653b5d98fea4de58eca772")
        self.assertEqual(span_id , "136eec09c948be26")
        self.assertEqual(sampled_flag , 1)
        self.assertIsNone(parent_span_id)
        self.assertEqual(tracestate , {})

    @mock.patch.dict(os.environ, {'b3':'8238c50fd8653b5d98fea4de58eca772-177eec09c948be26-1'})
    def test_extract_b3format_valid_format_without_parent_span_present(self):
        extracted_context = self.b3_composite_env_propagator_object.extract(getter = getter, carrier = os.environ)
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(extracted_context)
        self.assertEqual(trace_id , "8238c50fd8653b5d98fea4de58eca772")
        self.assertEqual(span_id , "177eec09c948be26")
        self.assertEqual(sampled_flag , 1)
        self.assertIsNone(parent_span_id)
        self.assertEqual(tracestate , {})

    @mock.patch.dict(os.environ, {'b3':'8128c50fd8653b5d-177eec09c948be26-1-e28bf981e15deb7f'})
    def test_extract_b3format_with_16_hex_char_traceid_and_parent_span_id_present(self):
        extracted_context = self.b3_composite_env_propagator_object.extract(getter = getter, carrier = os.environ)
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(extracted_context)
        trace_id_match = re.fullmatch(self.b3_object._trace_id_regex, trace_id)
        span_id_match = re.fullmatch(self.b3_object._span_id_regex, span_id)
        self.assertEqual(trace_id , "00000000000000008128c50fd8653b5d")
        self.assertEqual(span_id , "177eec09c948be26")
        self.assertEqual(sampled_flag , 1)
        self.assertNotEqual(trace_id_match , None)
        self.assertNotEqual(span_id_match , None)

    @mock.patch.dict(os.environ, {'b3':'8128c50fd8653b5d-177eec09c948be26-1'})
    def test_extract_b3format_with_16_hex_char_traceid_and_no_parent_span_id(self):
        extracted_context = self.b3_composite_env_propagator_object.extract(getter = getter, carrier = os.environ)
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(extracted_context)
        trace_id_match = re.fullmatch(self.b3_object._trace_id_regex, trace_id)
        span_id_match = re.fullmatch(self.b3_object._span_id_regex, span_id)
        self.assertEqual(trace_id , "00000000000000008128c50fd8653b5d")
        self.assertEqual(span_id , "177eec09c948be26")
        self.assertEqual(sampled_flag , 1)
        self.assertNotEqual(trace_id_match , None)
        self.assertNotEqual(span_id_match , None)

    @mock.patch.dict(os.environ, {'b3':'8128c50-177eec09c948be26-1-e28bf981e15deb7f'})
    def test_extract_b3format_invalid_traceid_in_environment_variable_with_parent_span_id_present(self):
        extracted_context = self.b3_composite_env_propagator_object.extract(getter = getter, carrier = os.environ)
        self.assertEqual(extracted_context , {})

    @mock.patch.dict(os.environ, {'b3':'8128c50-177eec09c948be26-1'})
    def test_extract_b3format_invalid_traceid_in_environment_variable_without_parent_span_id_present(self):
        extracted_context = self.b3_composite_env_propagator_object.extract(getter = getter, carrier = os.environ)
        self.assertEqual(extracted_context , {})

    @mock.patch.dict(os.environ, {'b3':'8238c50fd8653b5d98fea4de58eca772-177eec09c-1-e28bf9eb7f'})
    def test_extract_b3format_invalid_span_id_in_environment_variable_with_parent_span_id_present(self):
        extracted_context = self.b3_composite_env_propagator_object.extract(getter = getter, carrier = os.environ)
        self.assertEqual(extracted_context , {})

    @mock.patch.dict(os.environ, {'b3':'8238c50fd8653b5d98fea4de58eca772-177eec09c-1'})
    def test_extract_b3format_invalid_span_id_in_environment_variable_without_parent_span_id_present(self):
        extracted_context = self.b3_composite_env_propagator_object.extract(getter = getter, carrier = os.environ)
        self.assertEqual(extracted_context , {})

    @mock.patch.dict(os.environ, {'b3':'8238c50fd8653b5d-177eec09c-1'})
    def test_extract_b3format_invalid_span_id_in_environment_variable_with_16_hex_char_traceid(self):
        extracted_context = self.b3_composite_env_propagator_object.extract(getter = getter, carrier = os.environ)
        self.assertEqual(extracted_context , {})

    @mock.patch.dict(os.environ, {'b3':'8238c50-177eec09c-1-e28bf9'})
    def test_extract_b3format_with_invalid_trace_id_and_span_id_and_parent_id_in_environment_variable(self):
        extracted_context = self.b3_composite_env_propagator_object.extract(getter = getter, carrier = os.environ)
        self.assertEqual(extracted_context , {})

    @mock.patch.dict(os.environ, {'b3':'8238c50ty8768698-177eec09c-a'})
    def test_extract_b3format_invalid_trace_id_and_span_id_and_sampled_in_environment_variable(self):
        extracted_context = self.b3_composite_env_propagator_object.extract(getter = getter, carrier = os.environ)
        self.assertEqual(extracted_context , {})

    @mock.patch.dict(os.environ, {})
    def test_extract_b3format_when_no_trace_details(self):
        extracted_context = self.b3_composite_env_propagator_object.extract(getter = getter, carrier = os.environ)
        self.assertEqual(extracted_context , {})

    # Test cases for extract_context

    @mock.patch.dict(os.environ, {})
    def test_extract_context_when_no_trace_details(self):
        extracted_context = self.b3_composite_env_propagator_object.extract_context()
        self.assertEqual(extracted_context , {})

    @mock.patch.dict(os.environ, {'b3':'8128c50fd8653b5d98fea4de58eca772-136eec09c948be26-1-e28bf981e15deb7f'})
    def test_extract_context_when_valid_format_in_environment_variable_with_parent_span_present(self):
        extracted_context = self.b3_composite_env_propagator_object.extract_context()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(extracted_context)
        self.assertEqual(trace_id , "8128c50fd8653b5d98fea4de58eca772")
        self.assertEqual(span_id , "136eec09c948be26")
        self.assertEqual(sampled_flag , 1)
        self.assertEqual(tracestate , {})

    @mock.patch.dict(os.environ, {'b3':'8238c50fd8653b5d98fea4de58eca772-177eec09c948be26-1'})
    def test_extract_context_when_valid_format_in_environment_variable_without_parent_span_present(self):
        extracted_context = self.b3_composite_env_propagator_object.extract_context()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(extracted_context)
        self.assertEqual(trace_id , "8238c50fd8653b5d98fea4de58eca772")
        self.assertEqual(span_id , "177eec09c948be26")
        self.assertEqual(sampled_flag , 1)
        self.assertEqual(tracestate , {})

    @mock.patch.dict(os.environ, {'b3':'8128c50fd8653b5d-177eec09c948be26-1-e28bf981e15deb7f'})
    def test_extract_context_when_valid_format_in_environment_variable_with_16_hex_char_traceid_and_parent_span_present(self):
        extracted_context = self.b3_composite_env_propagator_object.extract_context()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(extracted_context)
        trace_id_match = re.fullmatch(self.b3_object._trace_id_regex, trace_id)
        span_id_match = re.fullmatch(self.b3_object._span_id_regex, span_id)
        self.assertEqual(trace_id , "00000000000000008128c50fd8653b5d")
        self.assertEqual(span_id , "177eec09c948be26")
        self.assertEqual(sampled_flag , 1)
        self.assertNotEqual(trace_id_match , None)
        self.assertNotEqual(span_id_match , None)

    @mock.patch.dict(os.environ, {'b3':'8128c50fd8653b5d-177eec09c948be26-1'})
    def test_extract_context_when_valid_format_in_environment_variable_with_16_hex_char_traceid_and_no_parent_span_present(self):
        extracted_context = self.b3_composite_env_propagator_object.extract_context()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(extracted_context)
        trace_id_match = re.fullmatch(self.b3_object._trace_id_regex, trace_id)
        span_id_match = re.fullmatch(self.b3_object._span_id_regex, span_id)
        self.assertEqual(trace_id , "00000000000000008128c50fd8653b5d")
        self.assertEqual(span_id , "177eec09c948be26")
        self.assertEqual(sampled_flag , 1)
        self.assertNotEqual(trace_id_match , None)
        self.assertNotEqual(span_id_match , None)

    @mock.patch.dict(os.environ, {'b3':'8128c50-177eec09c948be26-1-e28bf981e15deb7f'})
    def test_extract_context_when_invalid_traceid_in_environment_variable_with_parent_span_present(self):
        extracted_context = self.b3_composite_env_propagator_object.extract_context()
        self.assertEqual(extracted_context , {})
        self.assertEqual(opentelemetry.trace.get_current_span(extracted_context), opentelemetry.trace.span.INVALID_SPAN)

    @mock.patch.dict(os.environ, {'b3':'8128c50-177eec09c948be26-1'})
    def test_extract_context_when_invalid_traceid_in_environment_variable_without_parent_span_present(self):
        extracted_context = self.b3_composite_env_propagator_object.extract_context()
        self.assertEqual(extracted_context , {})
        self.assertEqual(opentelemetry.trace.get_current_span(extracted_context), opentelemetry.trace.span.INVALID_SPAN)

    @mock.patch.dict(os.environ, {'b3':'8238c50fd8653b5d98fea4de58eca772-177eec09c-1-e28bf9eb7f233342'})
    def test_extract_context_when_invalid_span_id_in_environment_variable_with_valid_parent_span_id_present(self):
        extracted_context = self.b3_composite_env_propagator_object.extract_context()
        self.assertEqual(extracted_context , {})
        self.assertEqual(opentelemetry.trace.get_current_span(extracted_context), opentelemetry.trace.span.INVALID_SPAN)

    @mock.patch.dict(os.environ, {'b3':'8238c50fd8653b5d98fea4de58eca772-177eec09c-1-e28bf9eb7f'})
    def test_extract_context_when_span_id_and_parent_span_id_invalid_in_environment_variable(self):
        extracted_context = self.b3_composite_env_propagator_object.extract_context()
        self.assertEqual(extracted_context , {})
        self.assertEqual(opentelemetry.trace.get_current_span(extracted_context), opentelemetry.trace.span.INVALID_SPAN)

    @mock.patch.dict(os.environ, {'b3':'8238c50fd8653b5d98fea4de58eca772-177eec09c-1'})
    def test_extract_context_when_invalid_span_id_in_environment_variable_without_parent_span_present(self):
        extracted_context = self.b3_composite_env_propagator_object.extract_context()
        self.assertEqual(extracted_context , {})
        self.assertEqual(opentelemetry.trace.get_current_span(extracted_context), opentelemetry.trace.span.INVALID_SPAN)

    @mock.patch.dict(os.environ, {'b3':'8238c50fd8653b5d-177eec09c-1'})
    def test_extract_context_when_invalid_span_id_in_environment_variable_with_16_hex_char_trace_id_and_without_parent_span_present(self):
        extracted_context = self.b3_composite_env_propagator_object.extract_context()
        self.assertEqual(extracted_context , {})
        self.assertEqual(opentelemetry.trace.get_current_span(extracted_context), opentelemetry.trace.span.INVALID_SPAN)

    @mock.patch.dict(os.environ, {'b3':'8238c50ty8768698-177eec09c-1-e28bf9'})
    def test_extract_context_when_trace_id_span_id_and_parent_span_id_invalid_in_environment_variable(self):
        extracted_context = self.b3_composite_env_propagator_object.extract_context()
        self.assertEqual(extracted_context , {})
        self.assertEqual(opentelemetry.trace.get_current_span(extracted_context), opentelemetry.trace.span.INVALID_SPAN)

    @mock.patch.dict(os.environ, {'b3':'8238c50ty8768698-177eec09c-a'})
    def test_extract_context_when_trace_id_span_id_and_sampled_invalid_in_environment_variable(self):
        extracted_context = self.b3_composite_env_propagator_object.extract_context()
        self.assertEqual(extracted_context , {})
        self.assertEqual(opentelemetry.trace.get_current_span(extracted_context), opentelemetry.trace.span.INVALID_SPAN)
