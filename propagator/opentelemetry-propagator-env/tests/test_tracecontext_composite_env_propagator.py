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
import unittest
from unittest import mock

import opentelemetry
from opentelemetry.propagators.textmap import DefaultGetter, DefaultSetter
from opentelemetry.propagators.env.composite_propagator import CompositeEnvPropagator
from opentelemetry.trace.propagation import tracecontext
from tests.utils import *

getter = DefaultGetter()

class TestTracecontextCompositeEnvPropagator(unittest.TestCase):
    def setUp(self):
        self.mock_carrier = {}
        self.composite_env_propagator_w3c_obj = CompositeEnvPropagator([tracecontext.TraceContextTextMapPropagator()])
        self.composite_env_propagator_None_obj = CompositeEnvPropagator(None)
        self.w3c_object = tracecontext.TraceContextTextMapPropagator()

    # Test cases for inject_to_carrier

    def test_inject_to_carrier_when_valid_context_with_baggage_attached_for_w3c(self):
        dummy_context = create_valid_context_with_baggage()
        token = opentelemetry.context.attach(dummy_context)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        self.mock_carrier = self.composite_env_propagator_w3c_obj.inject_to_carrier()
        opentelemetry.context.detach(token)
        self.assertEqual(self.mock_carrier.get("traceparent") , '00'+'-'+str(traceid)+'-'+str(spanid)+'-'+'0'+str(sampled))
        self.assertIsNone(self.mock_carrier.get("b3"))
        self.assertIsNone(self.mock_carrier.get("baggage"))

    def test_inject_to_carrier_when_invalid_context_with_baggage_attached_for_w3c(self):
        current_context = create_invalid_context_with_baggage()
        token = opentelemetry.context.attach(current_context)
        self.mock_carrier = self.composite_env_propagator_w3c_obj.inject_to_carrier()
        opentelemetry.context.detach(token)
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertIsNone(self.mock_carrier.get("b3"))
        self.assertIsNone(self.mock_carrier.get("baggage"))

    def test_inject_to_carrier_when_valid_context_with_baggage_passed_as_param_for_w3c(self):
        dummy_context = create_valid_context_with_baggage()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        self.mock_carrier = self.composite_env_propagator_w3c_obj.inject_to_carrier(context = dummy_context)
        self.assertEqual(self.mock_carrier.get("traceparent") , '00'+'-'+str(traceid)+'-'+str(spanid)+'-'+'0'+str(sampled))
        self.assertIsNone(self.mock_carrier.get("b3"))
        self.assertIsNone(self.mock_carrier.get("baggage"))

    def test_inject_to_carrier_when_valid_context_without_baggage_passed_as_param_for_w3c(self):
        dummy_context = create_dummy_context_with_parent_span()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        self.mock_carrier = self.composite_env_propagator_w3c_obj.inject_to_carrier(context = dummy_context)
        self.assertEqual(self.mock_carrier.get("traceparent") , '00'+'-'+str(traceid)+'-'+str(spanid)+'-'+'0'+str(sampled))
        self.assertIsNone(self.mock_carrier.get("b3"))
        self.assertIsNone(self.mock_carrier.get("baggage"))

    def test_inject_to_carrier_with_invalid_context_with_baggage_passed_as_param_for_w3c(self):
        dummy_context = create_invalid_context_with_baggage()
        self.mock_carrier = self.composite_env_propagator_w3c_obj.inject_to_carrier(context = dummy_context)
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertIsNone(self.mock_carrier.get("b3"))
        self.assertIsNone(self.mock_carrier.get("baggage"))


    def test_inject_to_carrier_when_context_attached_and_context_passed_as_param_are_different_for_w3c(self):
        dummy_context = create_valid_context_with_baggage()
        token = opentelemetry.context.attach(dummy_context)
        context_passed = create_valid_context_with_baggage2()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(context_passed)
        traceid2, spanid2, sampled2, parentspanid2, tracestate2 = get_details_from_context(dummy_context)
        self.mock_carrier = self.composite_env_propagator_w3c_obj.inject_to_carrier(context_passed)
        opentelemetry.context.detach(token)
        self.assertIsNone(self.mock_carrier.get("b3"))
        self.assertEqual(self.mock_carrier.get("traceparent") , '00'+'-'+str(traceid)+'-'+str(spanid)+'-'+'0'+str(sampled))
        self.assertNotEqual(self.mock_carrier.get("traceparent") , '00'+'-'+str(traceid2)+'-'+str(spanid2)+'-'+'0'+str(sampled2))
        self.assertIsNone(self.mock_carrier.get("baggage"))

    ## Test cases for inject

    def test_inject_w3cformat_invalid_context_passed_as_param(self):
        test_context = create_invalid_context()
        self.composite_env_propagator_w3c_obj.inject(carrier = self.mock_carrier, context = test_context, setter = DefaultSetter())
        self.assertIsNone(self.mock_carrier.get("traceparent"))

    def test_inject_w3cformat_valid_context_passed_as_param(self):
        test_context = create_dummy_context_with_parent_span()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(test_context)
        self.composite_env_propagator_w3c_obj.inject(carrier = self.mock_carrier, context = test_context, setter = DefaultSetter())
        self.assertEqual(self.mock_carrier.get("traceparent") , "00"+"-"+str(trace_id)+"-"+str(span_id)+"-"+"0"+str(int(sampled_flag)))

    def test_inject_w3cformat_valid_context_attached(self):
        test_context = create_dummy_context()
        token = opentelemetry.context.attach(test_context)
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(test_context)
        self.composite_env_propagator_w3c_obj.inject(carrier = self.mock_carrier, setter = DefaultSetter())
        opentelemetry.context.detach(token)
        self.assertEqual(self.mock_carrier.get("traceparent") , "00"+"-"+str(trace_id)+"-"+str(span_id)+"-"+"0"+str(int(sampled_flag)))

    def test_inject_w3cformat_invalid_context_attached(self):
        test_context = create_invalid_context()
        token = opentelemetry.context.attach(test_context)
        self.composite_env_propagator_w3c_obj.inject(carrier = self.mock_carrier, setter = DefaultSetter())
        opentelemetry.context.detach(token)
        self.assertIsNone(self.mock_carrier.get("traceparent"))

    def test_inject_w3cformat_when_context_attached_and_context_passed_as_param_are_different(self):
        dummy_context = create_dummy_context2()
        token = opentelemetry.context.attach(dummy_context)
        context_passed = create_dummy_context()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(context_passed)
        traceid2, spanid2, sampled2, parentspanid2, tracestate2 = get_details_from_context(dummy_context)
        self.composite_env_propagator_w3c_obj.inject(carrier = self.mock_carrier, context = context_passed, setter = DefaultSetter())
        opentelemetry.context.detach(token)
        self.assertEqual(self.mock_carrier.get("traceparent") , '00'+'-'+str(traceid)+'-'+str(spanid)+'-'+'0'+str(sampled))


    # Test cases for extract

    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd8653b5d98fea4de58eca772-136eec09c948be26-01"})
    def test_extract_valid_w3cformat_present_in_environment_variable(self):
        extracted_context = self.composite_env_propagator_w3c_obj.extract(getter = getter, carrier = os.environ)
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(extracted_context)
        self.assertEqual(trace_id , "8128c50fd8653b5d98fea4de58eca772")
        self.assertEqual(span_id , "136eec09c948be26")
        self.assertEqual(sampled_flag , 1)
        self.assertEqual(tracestate , {})

    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd8653b5d98fea4de58eca772-136eec06-a"})
    def test_extract_w3cformat_with_invalid_span_id(self):
        extracted_context = self.composite_env_propagator_w3c_obj.extract(getter = getter, carrier = os.environ)
        self.assertEqual(opentelemetry.trace.get_current_span(extracted_context), opentelemetry.trace.span.INVALID_SPAN)

    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50ed865ca77-136eec06ae45ae57-1"})
    def test_extract_w3cformat_with_invalid_trace_id_having_16_hex_char(self):
        extracted_context = self.composite_env_propagator_w3c_obj.extract(getter = getter, carrier = os.environ)
        self.assertEqual( opentelemetry.trace.get_current_span(extracted_context), opentelemetry.trace.span.INVALID_SPAN)

    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd865ca77-136eec06-1"})
    def test_extract_w3cformat_with_invalid_trace_id_and_span_id(self):
        extracted_context = self.composite_env_propagator_w3c_obj.extract(getter = getter, carrier = os.environ)
        self.assertEqual(opentelemetry.trace.get_current_span(extracted_context), opentelemetry.trace.span.INVALID_SPAN)

    def test_extract_when_no_trace_details_in_w3c_format(self):
        extracted_context = self.composite_env_propagator_w3c_obj.extract(getter = getter, carrier = os.environ)
        self.assertEqual(opentelemetry.trace.get_current_span(extracted_context), opentelemetry.trace.span.INVALID_SPAN)

    # test cases for extract_context

    def test_extract_context_when_no_trace_details(self):
        extracted_context = self.composite_env_propagator_w3c_obj.extract_context()
        self.assertEqual(opentelemetry.trace.get_current_span(extracted_context), opentelemetry.trace.span.INVALID_SPAN)

    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd8653b5d98fea4de58eca772-136eec09c948be26-01"})
    def test_extract_context_valid_w3cformat_in_environment_variable(self):
        extracted_context = self.composite_env_propagator_w3c_obj.extract_context()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(extracted_context)
        self.assertEqual(trace_id , "8128c50fd8653b5d98fea4de58eca772")
        self.assertEqual(span_id , "136eec09c948be26")
        self.assertEqual(sampled_flag , 1)
        self.assertEqual(tracestate , {})

    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd8653b5d98fea4de58eca772-136eec06-a"})
    def test_extract_context_w3cformat_with_invalid_span_id(self):
        extracted_context = self.composite_env_propagator_w3c_obj.extract_context()
        self.assertEqual(opentelemetry.trace.get_current_span(extracted_context), opentelemetry.trace.span.INVALID_SPAN)

    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50ed865ca77-136eec06ae45ae57-1"})
    def test_extract_context_w3cformat_with_invalid_trace_id_having_16_hex_char(self):
        extracted_context = self.composite_env_propagator_w3c_obj.extract_context()
        self.assertEqual(opentelemetry.trace.get_current_span(extracted_context), opentelemetry.trace.span.INVALID_SPAN)

    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd865ca77-136eec06-1"})
    def test_extract_context_w3cformat_with_invalid_trace_id_and_span_id(self):
        extracted_context = self.composite_env_propagator_w3c_obj.extract_context()
        self.assertEqual(opentelemetry.trace.get_current_span(extracted_context), opentelemetry.trace.span.INVALID_SPAN)
