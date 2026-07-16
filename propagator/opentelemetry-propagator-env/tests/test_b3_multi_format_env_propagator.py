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
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.propagators.env.propagator import EnvPropagator
from opentelemetry.propagators.textmap import DefaultGetter, DefaultSetter
from tests.utils import *

getter = DefaultGetter()
class TestB3MultiEnvPropagator(unittest.TestCase):
    def setUp(self):
        self.mock_carrier = {}
        self.env_propagator_b3_obj = EnvPropagator(B3MultiFormat())
        self.env_propagator_None_obj = EnvPropagator(None)
        self.b3_object = B3MultiFormat()

    # Test cases for inject_to_carrier

    def test_inject_to_carrier_when_None_object_passed_to_env_propagator(self):
        dummy_context = create_dummy_context()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        env_None = self.env_propagator_None_obj.inject_to_carrier(dummy_context)
        self.assertEqual(env_None.get("traceparent") , '00'+'-'+str(traceid)+'-'+str(spanid)+'-'+'0'+str(sampled))


    def test_inject_to_carrier_when_None_object_passed_to_env_propagator_and_context_attached(self):
        dummy_context = create_dummy_context()
        token = opentelemetry.context.attach(dummy_context)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        env_None = self.env_propagator_None_obj.inject_to_carrier()
        opentelemetry.context.detach(token)
        self.assertEqual(env_None.get("traceparent") , '00'+'-'+str(traceid)+'-'+str(spanid)+'-'+'0'+str(sampled))


    def test_inject_to_carrier_when_context_attached_has_valid_span_context(self):
        dummy_context = create_dummy_context()
        token = opentelemetry.context.attach(dummy_context)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        env_b3 = self.env_propagator_b3_obj.inject_to_carrier()
        opentelemetry.context.detach(token)
        self.assertEqual(env_b3.get("x-b3-traceid") , str(traceid))
        self.assertEqual(env_b3.get("x-b3-spanid") , str(spanid))
        self.assertIsNone(env_b3.get("x-b3-parentspanid"))
        self.assertEqual(env_b3.get("x-b3-sampled") , str(sampled))
        self.assertIsNone(env_b3.get("traceparent"))
        self.assertIsNone(env_b3.get("b3"))

    def test_inject_to_carrier_when_context_passed_as_param_is_None(self):
        dummy_context = create_dummy_context()
        token = opentelemetry.context.attach(dummy_context)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        env_b3 = self.env_propagator_b3_obj.inject_to_carrier(None)
        opentelemetry.context.detach(token)
        self.assertEqual(env_b3.get("x-b3-traceid") , str(traceid))
        self.assertEqual(env_b3.get("x-b3-spanid") , str(spanid))
        self.assertIsNone(env_b3.get("x-b3-parentspanid"))
        self.assertEqual(env_b3.get("x-b3-sampled") , str(sampled))
        self.assertIsNone(env_b3.get("traceparent"))
        self.assertIsNone(env_b3.get("b3"))

    def test_inject_to_carrier_when_valid_context_is_passed_as_param(self):
        context_passed = create_dummy_context()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(context_passed)
        env_b3 = self.env_propagator_b3_obj.inject_to_carrier(context_passed)
        self.assertEqual(env_b3.get("x-b3-traceid") , str(traceid))
        self.assertEqual(env_b3.get("x-b3-spanid") , str(spanid))
        self.assertIsNone(env_b3.get("x-b3-parentspanid"))
        self.assertEqual(env_b3.get("x-b3-sampled") , str(sampled))
        self.assertIsNone(env_b3.get("traceparent"))
        self.assertIsNone( env_b3.get("b3"))


    def test_inject_to_carrier_when_context_attached_and_context_passed_as_param_are_different(self):
        dummy_context = create_dummy_context2()
        token = opentelemetry.context.attach(dummy_context)
        context_passed = create_dummy_context()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(context_passed)
        traceid2, spanid2, sampled2, parentspanid2, tracestate2 = get_details_from_context(dummy_context)
        env_b3 = self.env_propagator_b3_obj.inject_to_carrier(context_passed)
        opentelemetry.context.detach(token)
        self.assertEqual(env_b3.get("x-b3-traceid") , str(traceid))
        self.assertEqual(env_b3.get("x-b3-spanid") , str(spanid))
        self.assertIsNone(env_b3.get("x-b3-parentspanid"))
        self.assertEqual(env_b3.get("x-b3-sampled") , str(sampled))  # sampled and sampled2 are equal to 0
        self.assertNotEqual(env_b3.get("x-b3-traceid") , str(traceid2))
        self.assertNotEqual(env_b3.get("x-b3-spanid") , str(spanid2))
        self.assertIsNone(env_b3.get("x-b3-parentspanid"))
        self.assertIsNone(env_b3.get("traceparent"))
        self.assertIsNone(env_b3.get("b3"))


    ## Test cases for extract_context

    def test_extract_context_when_no_trace_details_in_b3_format(self):
        extracted_context_b3 = self.env_propagator_b3_obj.extract_context()
        self.assertEqual(extracted_context_b3 , {})

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c50fd8653b5d98fea4de58eca772"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136eec09c948be26"})
    @mock.patch.dict(os.environ, {"x-b3-sampled": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    def test_extract_context_when_b3_valid_format(self):
        extracted_context = self.env_propagator_b3_obj.extract_context()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(extracted_context)
        self.assertEqual(traceid , '8128c50fd8653b5d98fea4de58eca772')
        self.assertEqual(spanid , '136eec09c948be26')
        self.assertEqual(sampled , 1)
        self.assertEqual(tracestate , {})
        self.assertIsNone(parentspanid)

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c5765"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136eec09c948be26"})
    @mock.patch.dict(os.environ, {"x-b3-sampled'": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    def test_extract_context_when_traceid_does_not_match_regex_for_b3_and_parent_span_id_present(self):
        extracted_context_b3 = self.env_propagator_b3_obj.extract_context()
        self.assertEqual(extracted_context_b3 , {})

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c5765"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136eec09c948be26"})
    @mock.patch.dict(os.environ, {"x-b3-sampled'": "1"})
    def test_extract_context_when_traceid_does_not_match_regex_for_b3_and_parent_span_id_not_present(self):
        extracted_context_b3 = self.env_propagator_b3_obj.extract_context()
        self.assertEqual(extracted_context_b3 , {})

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c50fd8653b5d98fea4de58eca772"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136ee"})
    @mock.patch.dict(os.environ, {"x-b3-sampled'": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    def test_extract_context_when_spanid_does_not_match_regex_for_b3_and_parent_span_id_present(self):
        extracted_context_b3 = self.env_propagator_b3_obj.extract_context()
        self.assertEqual(extracted_context_b3 , {})

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c50fd8653b5d98fea4de58eca772"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136ee"})
    @mock.patch.dict(os.environ, {"x-b3-sampled'": "1"})
    def test_extract_context_when_spanid_does_not_match_regex_for_b3_and_parent_span_id_not_present(self):
        extracted_context_b3 = self.env_propagator_b3_obj.extract_context()
        self.assertEqual(extracted_context_b3 , {})

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c50fd8653b5d98fea4de58eca772"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136ee"})
    def test_extract_context_when_traceid_is_valid_and_spanid_does_not_match_regex_for_b3(self):
        extracted_context_b3 = self.env_propagator_b3_obj.extract_context()
        self.assertEqual(extracted_context_b3 , {})

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c5765"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136ee"})
    @mock.patch.dict(os.environ, {"x-b3-sampled'": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    def test_extract_context_when_traceid_and_spanid_do_not_match_regex_for_b3_and_parent_span_id_present(self):
        extracted_context_b3 = self.env_propagator_b3_obj.extract_context()
        self.assertEqual(extracted_context_b3 , {})

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c5765"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136ee"})
    @mock.patch.dict(os.environ, {"x-b3-sampled'": "1"})
    def test_extract_context_when_traceid_and_spanid_do_not_match_regex_for_b3_and_parent_span_id_not_present(self):
        extracted_context_b3 = self.env_propagator_b3_obj.extract_context()
        self.assertEqual(extracted_context_b3 , {})

    @mock.patch.dict(os.environ, {"b3'": "8128c5-136ee"})
    def test_extract_context_when_traceid_and_spanid_are_invalid(self):
        extracted_context_b3 = self.env_propagator_b3_obj.extract_context()
        self.assertEqual(extracted_context_b3 , {})


    ## Test cases for inject

    def test_inject_b3format_when_valid_context_is_passed_as_param_and_parent_span_id_is_present(self):
        test_context = create_dummy_context_with_parent_span()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(test_context)
        self.env_propagator_b3_obj.inject(carrier = self.mock_carrier, context = test_context, setter = DefaultSetter())
        self.assertEqual(self.mock_carrier.get("x-b3-traceid") , str(trace_id))
        self.assertEqual(self.mock_carrier.get("x-b3-spanid") , str(span_id))
        self.assertEqual(self.mock_carrier.get("x-b3-parentspanid") , str(parent_span_id))
        self.assertEqual(self.mock_carrier.get("x-b3-sampled") , str(sampled_flag))
        self.assertIsNone(self.mock_carrier.get("b3"))


    def test_inject_b3format_when_valid_context_is_passed_as_param_and_parent_span_id_is_not_present(self):
        test_context = create_dummy_context()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(test_context)
        self.env_propagator_b3_obj.inject(carrier = self.mock_carrier, context = test_context, setter = DefaultSetter())
        self.assertEqual(self.mock_carrier.get("x-b3-traceid") , str(trace_id))
        self.assertEqual(self.mock_carrier.get("x-b3-spanid") , str(span_id))
        self.assertEqual(self.mock_carrier.get("x-b3-sampled") , str(sampled_flag))
        self.assertIsNone(self.mock_carrier.get("b3"))

    def test_inject_b3format_when_invalid_context_passed_as_param_and_parent_span_id_not_present(self):
        test_context = create_invalid_context()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(test_context)
        self.env_propagator_b3_obj.inject(carrier = self.mock_carrier, context = test_context, setter = DefaultSetter())
        self.assertIsNone(self.mock_carrier.get("x-b3-traceid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-spanid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-sampled"))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertIsNone(self.mock_carrier.get("b3"))

    def test_inject_b3format_when_valid_context_attached_and_parent_span_id_present(self):
        test_context = create_dummy_context_with_parent_span()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(test_context)
        token = opentelemetry.context.attach(test_context)
        self.env_propagator_b3_obj.inject(carrier = self.mock_carrier, context = test_context, setter = DefaultSetter())
        opentelemetry.context.detach(token)
        self.assertEqual(self.mock_carrier.get("x-b3-traceid") , str(trace_id))
        self.assertEqual(self.mock_carrier.get("x-b3-spanid") , str(span_id))
        self.assertEqual(self.mock_carrier.get("x-b3-parentspanid") , str(parent_span_id))
        self.assertEqual(self.mock_carrier.get("x-b3-sampled") , str(sampled_flag))
        self.assertIsNone(self.mock_carrier.get("b3"))

    def test_inject_b3format_when_invalid_context_attached_and_parent_span_id_not_present(self):
        test_context = create_invalid_context()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(test_context)
        token = opentelemetry.context.attach(test_context)
        self.env_propagator_b3_obj.inject(carrier = self.mock_carrier, setter = DefaultSetter())
        opentelemetry.context.detach(token)
        self.assertIsNone(self.mock_carrier.get("x-b3-traceid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-spanid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-sampled"))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertIsNone(self.mock_carrier.get("b3"))


    def test_inject_b3format_when_valid_context_attached_and_parent_span_id_not_present(self):
        test_context = create_dummy_context()
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(test_context)
        token = opentelemetry.context.attach(test_context)
        self.env_propagator_b3_obj.inject(carrier = self.mock_carrier, setter = DefaultSetter())
        opentelemetry.context.detach(token)
        self.assertEqual(self.mock_carrier.get("x-b3-traceid") , str(trace_id))
        self.assertEqual(self.mock_carrier.get("x-b3-spanid") , str(span_id))
        self.assertEqual(self.mock_carrier.get("x-b3-sampled") , str(sampled_flag))
        self.assertIsNone(self.mock_carrier.get("b3"))

    def test_inject_when_context_attached_and_context_passed_as_param_are_different(self):
        dummy_context = create_dummy_context2()
        token = opentelemetry.context.attach(dummy_context)
        context_passed = create_dummy_context_with_parent_span()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(context_passed)
        traceid2, spanid2, sampled2, parentspanid2, tracestate2 = get_details_from_context(dummy_context)
        self.env_propagator_b3_obj.inject(carrier = self.mock_carrier, context = context_passed, setter = DefaultSetter())
        opentelemetry.context.detach(token)
        self.assertEqual(self.mock_carrier.get("x-b3-traceid") , str(traceid))
        self.assertEqual(self.mock_carrier.get("x-b3-spanid") , str(spanid))
        self.assertEqual(self.mock_carrier.get("x-b3-parentspanid") , str(parentspanid))
        self.assertEqual(self.mock_carrier.get("x-b3-sampled") , str(sampled))
        self.assertNotEqual(self.mock_carrier.get("x-b3-traceid") , str(traceid2))
        self.assertNotEqual(self.mock_carrier.get("x-b3-spanid") , str(spanid2))
        self.assertNotEqual(self.mock_carrier.get("x-b3-parentspanid") , (parentspanid2))  # sampled and sampled2 are equal to 0
        self.assertIsNone(self.mock_carrier.get("b3"))

    ## Test cases for b3 extract

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c50fd8653b5d98fea4de58eca772"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136eec09c948be26"})
    @mock.patch.dict(os.environ, {"x-b3-sampled": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    def test_extract_valid_b3format(self):
        extracted_context = self.env_propagator_b3_obj.extract(getter = getter, carrier = os.environ)
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(extracted_context)
        self.assertEqual(trace_id , "8128c50fd8653b5d98fea4de58eca772")
        self.assertEqual(span_id , "136eec09c948be26")
        self.assertEqual(sampled_flag , 1)
        self.assertEqual(tracestate , {})

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8238c50fd8653b5d98fea4de58eca772"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "177eec09c948be26"})
    @mock.patch.dict(os.environ, {"x-b3-sampled": "1"})
    def test_extract_valid_b3format_without_parent_span_id(self):
        extracted_context = self.env_propagator_b3_obj.extract(getter = getter, carrier = os.environ)
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(extracted_context)
        self.assertEqual(trace_id , "8238c50fd8653b5d98fea4de58eca772")
        self.assertEqual(span_id , "177eec09c948be26")
        self.assertEqual(sampled_flag , 1)
        self.assertEqual(tracestate , {})

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c5"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136eec"})
    @mock.patch.dict(os.environ, {"x-b3-sampled": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    def test_extract_invalid_b3format(self):
        extracted_context = self.env_propagator_b3_obj.extract(getter = getter, carrier = os.environ)
        self.assertEqual(extracted_context , {})


    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c50fd8653b5d"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "177eec09c948be26"})
    @mock.patch.dict(os.environ, {"x-b3-sampled": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    def test_extract_16_hex_char_trace_id_and_parent_span_id_present(self):
        extracted_context = self.env_propagator_b3_obj.extract(getter = getter, carrier = os.environ)
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(extracted_context)
        trace_id_match = re.fullmatch(self.b3_object._trace_id_regex, trace_id)
        span_id_match = re.fullmatch(self.b3_object._span_id_regex, span_id)
        self.assertNotEqual(trace_id , "8128c50fd8653b5d")
        self.assertEqual(trace_id , "00000000000000008128c50fd8653b5d")
        self.assertEqual(span_id , "177eec09c948be26")
        self.assertEqual(sampled_flag , 1)
        self.assertNotEqual(trace_id_match , None)
        self.assertNotEqual(span_id_match , None)

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c50fd8653b5d"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "177eec09c948be26"})
    @mock.patch.dict(os.environ, {"x-b3-sampled": "1"})
    def test_extract_16_hex_char_trace_id_and_no_parent_span_id_present(self):
        extracted_context = self.env_propagator_b3_obj.extract(getter = getter, carrier = os.environ)
        trace_id, span_id, sampled_flag, parent_span_id, tracestate = get_details_from_context(extracted_context)
        trace_id_match = re.fullmatch(self.b3_object._trace_id_regex, trace_id)
        span_id_match = re.fullmatch(self.b3_object._span_id_regex, span_id)
        self.assertNotEqual(trace_id , "8128c50fd8653b5d")
        self.assertEqual(trace_id , "00000000000000008128c50fd8653b5d")
        self.assertEqual(span_id , "177eec09c948be26")
        self.assertEqual(sampled_flag , 1)
        self.assertNotEqual(trace_id_match , None)
        self.assertNotEqual(span_id_match , None)
