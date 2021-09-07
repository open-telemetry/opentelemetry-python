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
from opentelemetry.propagators.env import EnvPropagator
from opentelemetry.trace.propagation import tracecontext
from opentelemetry.propagators.textmap import DefaultGetter, DefaultSetter

from tests.utils import create_invalid_context, create_dummy_context, get_details_from_context, create_dummy_context2,create_dummy_context3,create_dummy_context_with_parent_span

getter = DefaultGetter()

class TestTracecontextEnvPropagator(unittest.TestCase):
    def setUp(self):
        self.mock_carrier = {}
        self.env_propagator_w3c_obj = EnvPropagator(tracecontext.TraceContextTextMapPropagator())
        self.env_propagator_None_obj = EnvPropagator(None)
        self.w3c_object = tracecontext.TraceContextTextMapPropagator()

    # Test cases for inject_to_carrier

    def test_inject_to_carrier_when_context_attached_has_invalid_span_context(self):
        current_context = create_invalid_context()
        token = opentelemetry.context.attach(current_context)

        env_w3c = self.env_propagator_w3c_obj.inject_to_carrier()
        opentelemetry.context.detach(token)
        self.assertEqual(env_w3c.get("traceparent") , None)
        self.assertEqual(env_w3c.get("b3") , None)

    ## test cases for inject_to_carrier when None object passed to propagator

    def test_when_None_object_passed_to_env_propagator_and_context_attached(self):
        dummy_context = create_dummy_context()
        token = opentelemetry.context.attach(dummy_context)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)

        env_None = self.env_propagator_None_obj.inject_to_carrier()
        opentelemetry.context.detach(token)
        self.assertEqual(env_None.get("traceparent") , '00'+'-'+str(traceid)+'-'+str(spanid)+'-'+'0'+str(sampled))


    def test_when_None_object_passed_to_env_propagator_and_context_passed_as_param(self):
        dummy_context = create_dummy_context()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)

        env_None = self.env_propagator_None_obj.inject_to_carrier(dummy_context)
        self.assertEqual(env_None.get("traceparent") , '00'+'-'+str(traceid)+'-'+str(spanid)+'-'+'0'+str(sampled))

    ## other test cases for inject_to_carrier

    def test_inject_to_carrier_when_attached_context_has_valid_span_context(self):
        dummy_context = create_dummy_context()
        token = opentelemetry.context.attach(dummy_context)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)

        env_w3c = self.env_propagator_w3c_obj.inject_to_carrier()
        opentelemetry.context.detach(token)
        self.assertEqual(env_w3c.get("traceparent") , '00'+'-'+str(traceid)+'-'+str(spanid)+'-'+'0'+str(sampled))
        self.assertEqual(env_w3c.get("b3") , None)

    def test_inject_to_carrier_when_context_passed_is_None(self):
        dummy_context = create_dummy_context()
        token = opentelemetry.context.attach(dummy_context)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(None)

        env_w3c = self.env_propagator_w3c_obj.inject_to_carrier(None)
        opentelemetry.context.detach(token)
        self.assertEqual(env_w3c.get("traceparent"), '00'+'-'+str(traceid)+'-'+str(spanid)+'-'+'0'+str(sampled))
        self.assertEqual(env_w3c.get("b3") , None)

    def test_inject_to_carrier_when_valid_context_is_passed_as_param(self):
        context_passed = create_dummy_context()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(context_passed)

        env_w3c = self.env_propagator_w3c_obj.inject_to_carrier(context_passed)
        self.assertEqual(env_w3c.get("traceparent") , '00'+'-'+str(traceid)+'-'+str(spanid)+'-'+'0'+str(sampled))
        self.assertEqual(env_w3c.get("b3") , None)

    def test_inject_to_carrier_when_attached_context_and_context_passed_as_param_are_different(self):
        dummy_context = create_dummy_context2()
        token = opentelemetry.context.attach(dummy_context)
        context_passed = create_dummy_context()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(context_passed)
        traceid2, spanid2, sampled2, parentspanid2, tracestate2 = get_details_from_context(dummy_context)
        env_w3c = self.env_propagator_w3c_obj.inject_to_carrier(context_passed)
        opentelemetry.context.detach(token)
        self.assertEqual(env_w3c.get("traceparent") , '00'+'-'+str(traceid)+'-'+str(spanid)+'-'+'0'+str(sampled))
        self.assertNotEqual(env_w3c.get("traceparent") , '00'+'-'+str(traceid2)+'-'+str(spanid2)+'-'+'0'+str(sampled2))
        self.assertEqual(env_w3c.get("b3") , None)


    ## Test cases for extract_context

    def test_extract_context_when_no_trace_details_in_w3c_format(self):
        extracted_context_w3c = self.env_propagator_w3c_obj.extract_context()
        self.assertEqual(extracted_context_w3c , {})

    @mock.patch.dict(os.environ, {'traceparent': '00-123-136eec09c948be26-1'})
    def test_extract_context_when_traceid_format_does_not_match_regex_for_w3c(self):
        extracted_context = self.env_propagator_w3c_obj.extract_context()
        self.assertEqual(extracted_context , {})

    @mock.patch.dict(os.environ, {'traceparent': '00-8128c50fd8653b5d98fea4de58eca772-136e-1'})
    def test_extract_context_when_spanid_format_does_not_match_regex_for_w3c(self):
        extracted_context = self.env_propagator_w3c_obj.extract_context()
        self.assertEqual(extracted_context , {})

    @mock.patch.dict(os.environ, {'traceparent': '00-123-136-1'})
    def test_extract_context_when_traceid_and_spanid_format_do_not_match_regex_for_w3c(self):
        extracted_context = self.env_propagator_w3c_obj.extract_context()
        self.assertEqual(extracted_context , {})

    @mock.patch.dict(os.environ, {'traceparent': '00-8128c50fd8653b5d98fea4de58eca772-136eec09c948be26-01'})
    @mock.patch.dict(os.environ, {'tracestate': 'congo=t61rcWkgMzE'})
    def test_extract_context_when_w3c_valid_format_has_tracestate(self):
        extracted_context = self.env_propagator_w3c_obj.extract_context()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(extracted_context)
        self.assertEqual(traceid , '8128c50fd8653b5d98fea4de58eca772')
        self.assertEqual(spanid , '136eec09c948be26')
        self.assertEqual(sampled , 1)
        self.assertEqual(tracestate , {'congo':'t61rcWkgMzE'})


    ## Test cases for inject

    def test_inject_w3cformat_invalid_context_passed_as_param(self):
        test_context = create_invalid_context()
        self.env_propagator_w3c_obj.inject(carrier = self.mock_carrier, context = test_context, setter = DefaultSetter())
        self.assertIsNone(self.mock_carrier.get("traceparent"))

    def test_inject_w3cformat_valid_context_passed_as_param(self):
        test_context = create_dummy_context_with_parent_span()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(test_context)
        self.env_propagator_w3c_obj.inject(carrier = self.mock_carrier, context = test_context, setter = DefaultSetter())
        self.assertEqual(self.mock_carrier["traceparent"] , "00"+"-"+str(trace_id)+"-"+str(span_id)+"-"+"0"+str(int(sampled_flag)))

    def test_inject_w3cformat_valid_context_attached(self):
        test_context = create_dummy_context()
        token = opentelemetry.context.attach(test_context)
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(test_context)
        self.env_propagator_w3c_obj.inject(carrier = self.mock_carrier, context = test_context, setter = DefaultSetter())
        opentelemetry.context.detach(token)
        self.assertEqual(self.mock_carrier["traceparent"] , "00"+"-"+str(trace_id)+"-"+str(span_id)+"-"+"0"+str(int(sampled_flag)))

    def test_inject_w3cformat_invalid_context_attached(self):
        test_context = create_invalid_context()
        token = opentelemetry.context.attach(test_context)
        self.env_propagator_w3c_obj.inject(carrier = self.mock_carrier, setter = DefaultSetter())
        opentelemetry.context.detach(token)
        self.assertIsNone(self.mock_carrier.get("traceparent"))

    def test_inject_w3cformat_when_context_attached_and_context_passed_as_param_are_different(self):
        dummy_context = create_dummy_context2()
        token = opentelemetry.context.attach(dummy_context)
        context_passed = create_dummy_context()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(context_passed)
        traceid2, spanid2, sampled2, parentspanid2, tracestate2 = get_details_from_context(dummy_context)
        self.env_propagator_w3c_obj.inject(carrier = self.mock_carrier, context = context_passed, setter = DefaultSetter())
        opentelemetry.context.detach(token)
        self.assertEqual(self.mock_carrier.get("traceparent") , '00'+'-'+str(traceid)+'-'+str(spanid)+'-'+'0'+str(sampled))

    ## Test cases for extract

    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd8653b5d98fea4de58eca772-136eec09c948be26-01"})
    def test_extract_when_valid_w3cformat_in_environment_variable(self):
        extracted_context = self.env_propagator_w3c_obj.extract(getter = getter, carrier = os.environ)
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(extracted_context)
        self.assertEqual(trace_id , "8128c50fd8653b5d98fea4de58eca772")
        self.assertEqual(span_id , "136eec09c948be26")
        self.assertEqual(sampled_flag , 1)
        self.assertEqual(tracestate , {})

    @mock.patch.dict(os.environ, {"traceparent": "00-8128ca772-136eec06-01"})
    def test_extract_when_invalid_w3cformat_in_environment_variable(self):
        extracted_context = self.env_propagator_w3c_obj.extract(getter = getter, carrier = os.environ)
        self.assertEqual(extracted_context , {})

    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd8653b5d98fea4de58eca772-136eec06-01"})
    def test_extract_w3cformat_with_invalid_span_id(self):
        extracted_context = self.env_propagator_w3c_obj.extract(getter = getter, carrier = os.environ)
        self.assertEqual(extracted_context , {})

    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd8653b5d-136eec06ae45ae57-01"})
    def test_extract_w3cformat_with_trace_id_having_16_hex_char(self):
        extracted_context = self.env_propagator_w3c_obj.extract(getter = getter, carrier = os.environ)
        self.assertEqual(extracted_context , {})

    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd865ca77-136eec06-01"})
    def test_extract_w3cformat_with_invalid_trace_id_and_span_id(self):
        extracted_context = self.env_propagator_w3c_obj.extract(getter = getter, carrier = os.environ)
        self.assertEqual(extracted_context , {})

    def test_extract_when_no_trace_details_in_w3c_format(self):
        extracted_context = self.env_propagator_w3c_obj.extract(getter = getter, carrier = os.environ)
        self.assertEqual(extracted_context , {})
