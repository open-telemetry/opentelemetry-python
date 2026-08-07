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
from opentelemetry import baggage
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.propagators.env.composite_propagator import CompositeEnvPropagator
from opentelemetry.propagators.textmap import DefaultGetter, DefaultSetter
from opentelemetry.trace.propagation import tracecontext
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from tests.utils import *

getter = DefaultGetter()
class TestB3MultiBaggageCompositeEnvPropagator(unittest.TestCase):
    def setUp(self):
        self.mock_carrier = {}
        self.composite_propagator_b3_baggage_object = CompositeEnvPropagator([B3MultiFormat(), W3CBaggagePropagator()])
        self.composite_propagator_None_object = CompositeEnvPropagator(None)

    # Test cases for inject_to_carrier

    def test_inject_to_carrier_when_valid_context_attached(self):
        valid_dummy_context = create_valid_context_with_baggage()
        token = opentelemetry.context.attach(valid_dummy_context)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(valid_dummy_context)
        self.mock_carrier = self.composite_propagator_b3_baggage_object.inject_to_carrier()
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertEqual(self.mock_carrier.get("x-b3-traceid") , str(traceid))
        self.assertEqual(self.mock_carrier.get("x-b3-spanid") , str(spanid))
        self.assertEqual(self.mock_carrier.get("x-b3-sampled") , str(sampled))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertEqual(self.mock_carrier.get("baggage") , "key1=1,key2=2")
        self.assertIsNone(self.mock_carrier.get("b3"))
        opentelemetry.context.detach(token)

    def test_inject_to_carrier_when_invalid_context_attached(self):
        invalid_context = create_invalid_context_with_baggage()
        token = opentelemetry.context.attach(invalid_context)
        self.mock_carrier = self.composite_propagator_b3_baggage_object.inject_to_carrier()
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertIsNone(self.mock_carrier.get("b3"))
        self.assertIsNone(self.mock_carrier.get("x-b3-traceid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-spanid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-sampled"))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertEqual(self.mock_carrier.get("baggage") , "test1=1,test2=2")
        opentelemetry.context.detach(token)

    def test_inject_to_carrier_when_valid_context_with_baggage_passed_as_param(self):
        valid_dummy_context = create_valid_context_with_baggage()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(valid_dummy_context)
        self.mock_carrier = self.composite_propagator_b3_baggage_object.inject_to_carrier(context = valid_dummy_context)
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertEqual(self.mock_carrier.get("x-b3-traceid") , str(traceid))
        self.assertEqual(self.mock_carrier.get("x-b3-spanid") , str(spanid))
        self.assertEqual(self.mock_carrier.get("x-b3-sampled") , str(sampled))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertEqual(self.mock_carrier.get("baggage") , "key1=1,key2=2")
        self.assertIsNone(self.mock_carrier.get("b3"))

    def test_inject_to_carrier_when_valid_context_with_parent_span_and_no_baggage_passed_as_param(self):
        valid_dummy_context = create_dummy_context_with_parent_span()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(valid_dummy_context)
        self.mock_carrier = self.composite_propagator_b3_baggage_object.inject_to_carrier(context = valid_dummy_context)
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertEqual(self.mock_carrier.get("x-b3-traceid") , str(traceid))
        self.assertEqual(self.mock_carrier.get("x-b3-spanid") , str(spanid))
        self.assertEqual(self.mock_carrier.get("x-b3-sampled") , str(sampled))
        self.assertEqual(self.mock_carrier.get("x-b3-parentspanid") , str(parentspanid))
        self.assertIsNotNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertIsNone(self.mock_carrier.get("baggage") )
        self.assertIsNone(self.mock_carrier.get("b3"))


    def test_inject_to_carrier_when_invalid_context_with_baggage_passed_as_param(self):
        invalid_dummy_context = create_invalid_context_with_baggage()
        self.mock_carrier = self.composite_propagator_b3_baggage_object.inject_to_carrier(context = invalid_dummy_context)
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertIsNone(self.mock_carrier.get("x-b3-traceid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-spanid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-sampled"))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertIsNone(self.mock_carrier.get("b3"))
        self.assertEqual(self.mock_carrier.get("baggage") , "test1=1,test2=2")


    def test_inject_to_carrier_when_attached_context_and_context_passed_as_param_are_different(self):
        dummy_context = create_valid_context_with_baggage()
        token = opentelemetry.context.attach(dummy_context)
        context_passed = create_valid_context_with_baggage2()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        traceid2, spanid2, sampled2, parentspanid2, tracestate2 = get_details_from_context(context_passed)
        self.mock_carrier = self.composite_propagator_b3_baggage_object.inject_to_carrier(context_passed)
        opentelemetry.context.detach(token)
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertEqual(self.mock_carrier.get("x-b3-traceid") , str(traceid2))
        self.assertEqual(self.mock_carrier.get("x-b3-spanid") , str(spanid2))
        self.assertEqual(self.mock_carrier.get("x-b3-sampled") , str(sampled2))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertNotEqual(self.mock_carrier.get("x-b3-traceid") , str(traceid))
        self.assertNotEqual(self.mock_carrier.get("x-b3-spanid") , str(spanid))
        self.assertEqual(self.mock_carrier.get("baggage") , "key3=1,key4=2")
        self.assertNotEqual(self.mock_carrier.get("baggage") , "key1=1,key2=2")
        self.assertIsNone(self.mock_carrier.get("b3"))


    # Test cases for inject

    ## Test cases for inject  when None object is passed to the propagator

    def test_inject_with_None_object_and_when_valid_context_with_baggage_attached(self):
        dummy_context = create_valid_context_with_baggage()
        token = opentelemetry.context.attach(dummy_context)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        self.composite_propagator_None_object.inject(carrier = self.mock_carrier, setter = DefaultSetter())
        self.assertEqual(self.mock_carrier.get("traceparent") , '00'+'-'+str(traceid)+'-'+str(spanid)+'-'+'0'+str(sampled))
        self.assertEqual(self.mock_carrier.get("baggage") , "key1=1,key2=2")
        self.assertIsNone(self.mock_carrier.get("x-b3-traceid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-spanid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-sampled"))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertIsNone(self.mock_carrier.get("b3"))
        opentelemetry.context.detach(token)

    def test_inject_with_None_object_and_when_invalid_context_with_baggage_attached(self):
        dummy_context = create_invalid_context_with_baggage()
        token = opentelemetry.context.attach(dummy_context)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        self.composite_propagator_None_object.inject(carrier = self.mock_carrier, setter = DefaultSetter())
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertEqual(self.mock_carrier.get("baggage") , "test1=1,test2=2")
        self.assertIsNone(self.mock_carrier.get("x-b3-traceid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-spanid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-sampled"))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertIsNone(self.mock_carrier.get("b3"))
        opentelemetry.context.detach(token)

    def test_inject_with_None_object_and_when_valid_context_with_baggage_passed_as_param(self):
        dummy_context = create_valid_context_with_baggage()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        self.composite_propagator_None_object.inject(carrier = self.mock_carrier, context = dummy_context, setter = DefaultSetter())
        self.assertEqual(self.mock_carrier.get("traceparent") , '00'+'-'+str(traceid)+'-'+str(spanid)+'-'+'0'+str(sampled))
        self.assertEqual(self.mock_carrier.get("baggage") , "key1=1,key2=2")
        self.assertIsNone(self.mock_carrier.get("x-b3-traceid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-spanid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-sampled"))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertIsNone(self.mock_carrier.get("b3"))

    def test_inject_with_None_object_and_when_invalid_context_with_baggage_passed_as_param(self):
        dummy_context = create_invalid_context_with_baggage()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        self.composite_propagator_None_object.inject(carrier = self.mock_carrier, context = dummy_context, setter = DefaultSetter())
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertEqual(self.mock_carrier.get("baggage") , "test1=1,test2=2")
        self.assertIsNone(self.mock_carrier.get("x-b3-traceid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-spanid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-sampled"))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertIsNone(self.mock_carrier.get("b3"))

    def test_inject_with_None_object_and_when_valid_context_attached_and_None_context_passed_as_param(self):
        dummy_context = create_valid_context_with_baggage()
        token = opentelemetry.context.attach(dummy_context)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        self.composite_propagator_None_object.inject(carrier = self.mock_carrier, context = None, setter = DefaultSetter())
        self.assertEqual(self.mock_carrier.get("traceparent") , '00'+'-'+str(traceid)+'-'+str(spanid)+'-'+'0'+str(sampled))
        self.assertEqual(self.mock_carrier.get("baggage") , "key1=1,key2=2")
        self.assertIsNone(self.mock_carrier.get("x-b3-traceid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-spanid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-sampled"))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertIsNone(self.mock_carrier.get("b3"))
        opentelemetry.context.detach(token)

    def test_inject_with_None_object_and_when_valid_context_with_no_baggage_attached(self):
        dummy_context = create_dummy_context_with_parent_span()
        token = opentelemetry.context.attach(dummy_context)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        self.composite_propagator_None_object.inject(carrier = self.mock_carrier, setter = DefaultSetter())
        self.assertEqual(self.mock_carrier.get("traceparent") , '00'+'-'+str(traceid)+'-'+str(spanid)+'-'+'0'+str(sampled))
        self.assertIsNone(self.mock_carrier.get("baggage"))
        self.assertIsNone(self.mock_carrier.get("x-b3-traceid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-spanid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-sampled"))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertIsNone(self.mock_carrier.get("b3"))
        opentelemetry.context.detach(token)

    ## other test cases for inject

    def test_inject_when_valid_context_with_no_baggage_attached(self):
        dummy_context = create_dummy_context_with_parent_span()
        token = opentelemetry.context.attach(dummy_context)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        self.composite_propagator_b3_baggage_object.inject(carrier = self.mock_carrier, setter = DefaultSetter())
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertIsNone(self.mock_carrier.get("baggage"))
        self.assertIsNone(self.mock_carrier.get("b3"))
        self.assertEqual(self.mock_carrier.get("x-b3-traceid") , str(traceid))
        self.assertEqual(self.mock_carrier.get("x-b3-spanid") , str(spanid))
        self.assertEqual(self.mock_carrier.get("x-b3-sampled") , str(sampled))
        self.assertEqual(self.mock_carrier.get("x-b3-parentspanid") , str(parentspanid))
        opentelemetry.context.detach(token)

    def test_inject_when_invalid_context_with_no_baggage_attached(self):
        invalid_dummy_context = create_invalid_context()
        token = opentelemetry.context.attach(invalid_dummy_context)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(invalid_dummy_context)
        self.composite_propagator_b3_baggage_object.inject(carrier = self.mock_carrier, setter = DefaultSetter())
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertIsNone(self.mock_carrier.get("baggage"))
        self.assertIsNone(self.mock_carrier.get("x-b3-traceid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-spanid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-sampled"))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertIsNone(self.mock_carrier.get("b3"))
        opentelemetry.context.detach(token)

    def test_inject_when_valid_context_with_baggage_attached(self):
        valid_dummy_context = create_valid_context_with_baggage()
        token = opentelemetry.context.attach(valid_dummy_context)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(valid_dummy_context)
        self.composite_propagator_b3_baggage_object.inject(carrier = self.mock_carrier, setter = DefaultSetter())
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertEqual(self.mock_carrier.get("baggage") , "key1=1,key2=2")
        self.assertEqual(self.mock_carrier.get("x-b3-traceid") , str(traceid))
        self.assertEqual(self.mock_carrier.get("x-b3-spanid") , str(spanid))
        self.assertEqual(self.mock_carrier.get("x-b3-sampled") , str(sampled))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertIsNone(self.mock_carrier.get("b3"))
        opentelemetry.context.detach(token)

    def test_inject_when_invalid_context_with_baggage_attached(self):
        dummy_context = create_invalid_context_with_baggage()
        token = opentelemetry.context.attach(dummy_context)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        self.composite_propagator_b3_baggage_object.inject(carrier = self.mock_carrier, setter = DefaultSetter())
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertEqual(self.mock_carrier.get("baggage") , "test1=1,test2=2")
        self.assertIsNone(self.mock_carrier.get("x-b3-traceid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-spanid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-sampled"))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid") )
        self.assertIsNone(self.mock_carrier.get("b3"))
        opentelemetry.context.detach(token)

    def test_inject_when_valid_context_with_parent_span_and_no_baggage_passed_as_param(self):
        dummy_context = create_dummy_context_with_parent_span()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        self.composite_propagator_b3_baggage_object.inject(carrier = self.mock_carrier, context = dummy_context, setter = DefaultSetter())
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertIsNone(self.mock_carrier.get("baggage"))
        self.assertEqual(self.mock_carrier.get("x-b3-traceid") , str(traceid))
        self.assertEqual(self.mock_carrier.get("x-b3-spanid") , str(spanid))
        self.assertEqual(self.mock_carrier.get("x-b3-sampled") , str(sampled))
        self.assertEqual(self.mock_carrier.get("x-b3-parentspanid") , str(parentspanid))
        self.assertIsNone(self.mock_carrier.get("b3"))

    def test_inject_when_invalid_context_with_no_baggage_passed_as_param(self):
        dummy_context = create_invalid_context()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        self.composite_propagator_b3_baggage_object.inject(carrier = self.mock_carrier, context = dummy_context, setter = DefaultSetter())
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertIsNone(self.mock_carrier.get("baggage"))
        self.assertIsNone(self.mock_carrier.get("x-b3-traceid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-spanid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-sampled"))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertIsNone(self.mock_carrier.get("b3"))

    def test_inject_when_valid_context_with_baggage_passed_as_param(self):
        dummy_context = create_valid_context_with_baggage()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        self.composite_propagator_b3_baggage_object.inject(carrier = self.mock_carrier, context = dummy_context, setter = DefaultSetter())
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertEqual(self.mock_carrier.get("baggage") , "key1=1,key2=2")
        self.assertEqual(self.mock_carrier.get("x-b3-traceid") , str(traceid))
        self.assertEqual(self.mock_carrier.get("x-b3-spanid") , str(spanid))
        self.assertEqual(self.mock_carrier.get("x-b3-sampled") , str(sampled))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertIsNone(self.mock_carrier.get("b3"))

    def test_inject_when_invalid_context_with_baggage_passed_as_param(self):
        dummy_context = create_invalid_context_with_baggage()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        self.composite_propagator_b3_baggage_object.inject(carrier = self.mock_carrier, context = dummy_context, setter = DefaultSetter())
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertEqual(self.mock_carrier.get("baggage") , "test1=1,test2=2")
        self.assertIsNone(self.mock_carrier.get("x-b3-traceid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-spanid"))
        self.assertIsNone(self.mock_carrier.get("x-b3-sampled"))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertIsNone(self.mock_carrier.get("b3"))

    def test_inject_when_context_with_baggage_attached_and_context_with_baggage_passed_as_param_are_different(self):
        dummy_context = create_valid_context_with_baggage()
        token = opentelemetry.context.attach(dummy_context)
        context_passed = create_valid_context_with_baggage2()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        traceid2, spanid2, sampled2, parentspanid2, tracestate2 = get_details_from_context(context_passed)
        self.composite_propagator_b3_baggage_object.inject(carrier = self.mock_carrier, context = context_passed, setter = DefaultSetter())
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertIsNone(self.mock_carrier.get("b3"))
        self.assertEqual(self.mock_carrier.get("x-b3-traceid") , str(traceid2))
        self.assertEqual(self.mock_carrier.get("x-b3-spanid") , str(spanid2))
        self.assertEqual(self.mock_carrier.get("x-b3-sampled") , str(sampled2))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertEqual(self.mock_carrier.get("baggage") , "key3=1,key4=2")
        opentelemetry.context.detach(token)

    def test_inject_when_context_attached_and_context_with_no_baggage_passed_as_param_are_different(self):
        dummy_context = create_dummy_context()
        token = opentelemetry.context.attach(dummy_context)
        context_passed = create_dummy_context2()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        traceid2, spanid2, sampled2, parentspanid2, tracestate2 = get_details_from_context(context_passed)
        self.composite_propagator_b3_baggage_object.inject(carrier = self.mock_carrier, context = context_passed, setter = DefaultSetter())
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertEqual(self.mock_carrier.get("x-b3-traceid") , str(traceid2))
        self.assertEqual(self.mock_carrier.get("x-b3-spanid") , str(spanid2))
        self.assertEqual(self.mock_carrier.get("x-b3-sampled") , str(sampled2))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertIsNone(self.mock_carrier.get("b3"))
        self.assertIsNone(self.mock_carrier.get("baggage"))
        opentelemetry.context.detach(token)

    def test_inject_when_valid_context_with_no_baggage_passed_as_param(self):
        dummy_context = create_dummy_context_with_parent_span()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        self.composite_propagator_b3_baggage_object.inject(carrier = self.mock_carrier, context = dummy_context, setter = DefaultSetter())
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertIsNone(self.mock_carrier.get("baggage"))
        self.assertEqual(self.mock_carrier.get("x-b3-traceid") , str(traceid))
        self.assertEqual(self.mock_carrier.get("x-b3-spanid") , str(spanid))
        self.assertEqual(self.mock_carrier.get("x-b3-sampled") , str(sampled))
        self.assertEqual(self.mock_carrier.get("x-b3-parentspanid") , str(parentspanid))
        self.assertIsNone(self.mock_carrier.get("b3"))

    def test_inject_when_traceid_has_16_hex_char(self):
        dummy_context = create_dummy_context3()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(dummy_context)
        self.composite_propagator_b3_baggage_object.inject(carrier = self.mock_carrier, context = dummy_context, setter = DefaultSetter())
        self.assertEqual(self.mock_carrier.get("x-b3-traceid") , str(traceid))
        self.assertEqual(self.mock_carrier.get("x-b3-spanid") , str(spanid))
        self.assertEqual(self.mock_carrier.get("x-b3-sampled") , str(sampled))
        self.assertIsNone(self.mock_carrier.get("x-b3-parentspanid"))
        self.assertIsNone(self.mock_carrier.get("b3"))
        self.assertIsNone(self.mock_carrier.get("traceparent"))
        self.assertIsNone(self.mock_carrier.get("baggage"))


    ## Test cases for extract

    def test_extract_when_no_trace_details(self):
        extracted_context = self.composite_propagator_b3_baggage_object.extract(carrier = os.environ, getter = getter)
        self.assertEqual(extracted_context , {})

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c50fd8653b5d98fea4de58eca772"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136eec09c948be26"})
    @mock.patch.dict(os.environ, {"x-b3-sampled": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd8653b5d98fea4de58eca772-136eec09c948be26-01"})
    @mock.patch.dict(os.environ, {"baggage": "key1=value1,=value2"})
    def test_extract_when_b3_and_baggage_are_valid(self):
        extracted_context = self.composite_propagator_b3_baggage_object.extract(carrier = os.environ, getter = getter)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(extracted_context)
        self.assertEqual(traceid , '8128c50fd8653b5d98fea4de58eca772')
        self.assertEqual(spanid , '136eec09c948be26')
        self.assertEqual(sampled , 1)
        val1 = baggage.get_baggage("key1", extracted_context)
        val2 = baggage.get_baggage("key2", extracted_context)
        self.assertEqual(val1 , "value1")
        self.assertIsNone(val2)

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c50fd8653b5d98fea4de58eca772"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136eec09c948be26"})
    @mock.patch.dict(os.environ, {"x-b3-sampled": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd8653b5d98fea4de58eca772-136eec09c948be26-01"})
    @mock.patch.dict(os.environ, {"baggage": "/value1"})
    def test_extract_when_b3_format_is_valid_and_baggage_invalid(self):
        extracted_context = self.composite_propagator_b3_baggage_object.extract(carrier = os.environ, getter = getter)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(extracted_context)
        self.assertEqual(traceid , '8128c50fd8653b5d98fea4de58eca772')
        self.assertEqual(spanid , '136eec09c948be26')
        self.assertEqual(sampled , 1)
        val = baggage.get_all(extracted_context)
        self.assertEqual(val , {})

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c50fd8653b5d98fea4de58eca772"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136eec09c"})
    @mock.patch.dict(os.environ, {"x-b3-sampled": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd8653b5d98fea4de58eca772-136eec09c-01"})
    @mock.patch.dict(os.environ, {"baggage": "key1=value1,key2=value2"})
    def test_extract_when_baggage_is_valid_but_b3_spanid_is_invalid(self):
        extracted_context = self.composite_propagator_b3_baggage_object.extract(carrier = os.environ, getter = getter)
        self.assertEqual(baggage.get_all(extracted_context), {'key1':'value1', 'key2':'value2'})

    @mock.patch.dict(os.environ, {"x-b3-traceid": "98fea4de58eca772"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136eec09c948be26"})
    @mock.patch.dict(os.environ, {"x-b3-sampled": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    @mock.patch.dict(os.environ, {"traceparent": "00-98fea4de58eca772-136eec09c948be26-01"})
    @mock.patch.dict(os.environ, {"baggage": "key1=value1,key2=value2"})
    def test_extract_when_baggage_is_valid_and_traceid_of_b3_has_16_hex_char(self):
        extracted_context = self.composite_propagator_b3_baggage_object.extract(carrier = os.environ, getter = getter)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(extracted_context)
        self.assertEqual(traceid , '000000000000000098fea4de58eca772')
        self.assertEqual(spanid , '136eec09c948be26')
        self.assertEqual(sampled , 1)
        val1 = baggage.get_baggage("key1", extracted_context)
        val2 = baggage.get_baggage("key2", extracted_context)
        self.assertEqual(val1 , "value1")
        self.assertEqual(val2 , "value2")

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c5"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136eec09c948be26"})
    @mock.patch.dict(os.environ, {"x-b3-sampled": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd8653b5d98fea4de-136eec09c948be26-01"})
    def test_extract_when_b3_traceid_is_invalid(self):
        extracted_context = self.composite_propagator_b3_baggage_object.extract(carrier = os.environ, getter = getter)
        self.assertEqual(extracted_context , {})

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c5"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136eec09c"})
    @mock.patch.dict(os.environ, {"x-b3-sampled": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd8653b5d98fea4de-136eec09c-01"})
    def test_extract_when_b3_traceid_and_spanid_are_invalid(self):
        extracted_context = self.composite_propagator_b3_baggage_object.extract(carrier = os.environ, getter = getter)
        self.assertEqual(extracted_context , {})

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c50fd8653b5d98fea4de58eca772"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136eec09c948be26"})
    @mock.patch.dict(os.environ, {"x-b3-sampled": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd8653b5d98fea4de58eca772-136eec09c948be26-01"})
    @mock.patch.dict(os.environ, {"baggage": "key1=value1,=value2"})
    def test_extract_when_a_baggage_key_is_not_passed(self):
        extracted_context = self.composite_propagator_b3_baggage_object.extract(carrier = os.environ, getter = getter)
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(extracted_context)
        self.assertEqual(traceid , '8128c50fd8653b5d98fea4de58eca772')
        self.assertEqual(spanid , '136eec09c948be26')
        self.assertEqual(sampled , 1)
        self.assertEqual(baggage.get_all(extracted_context) , {'key1':'value1','':'value2'})

    @mock.patch.dict(os.environ, {"baggage": "example1-value1;example2-value2"})
    def test_extract_baggage_invalid_format(self):
        extracted_context = self.composite_propagator_b3_baggage_object.extract(carrier = os.environ, getter = getter)
        self.assertEqual(extracted_context , {})

    @mock.patch.dict(os.environ, {"baggage": "example1=value1%2Cvalue2,example2=value3%2Cvalue4"})
    def test_extract_when_baggage_with_valid_format_has_commas_in_values(self):
        extracted_context = self.composite_propagator_b3_baggage_object.extract(carrier = os.environ, getter = getter)
        self.assertEqual(baggage.get_all(extracted_context) , {'example1':'value1,value2', 'example2':'value3,value4'})


    # test cases for extract_context

    def test_extract_context_when_no_trace_details(self):
        extracted_context = self.composite_propagator_b3_baggage_object.extract_context()
        self.assertEqual(extracted_context ,{})

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c50fd8653b5d98fea4de58eca772"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136eec09c948be26"})
    @mock.patch.dict(os.environ, {"x-b3-sampled": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd8653b5d98fea4de58eca772-136eec09c948be26-01"})
    @mock.patch.dict(os.environ, {"baggage": "key1=value1,=value2"})
    def test_extract_context_when_b3_and_baggage_are_valid(self):
        extracted_context = self.composite_propagator_b3_baggage_object.extract_context()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(extracted_context)
        self.assertEqual(traceid , '8128c50fd8653b5d98fea4de58eca772')
        self.assertEqual(spanid , '136eec09c948be26')
        self.assertEqual(sampled , 1)
        val1 = baggage.get_baggage("key1", extracted_context)
        val2 = baggage.get_baggage("key2", extracted_context)
        self.assertEqual(val1 , "value1")
        self.assertIsNone(val2)

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c50fd8653b5d98fea4de58eca772"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136eec09c948be26"})
    @mock.patch.dict(os.environ, {"x-b3-sampled": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd8653b5d98fea4de58eca772-136eec09c948be26-01"})
    @mock.patch.dict(os.environ, {"baggage": "=value1"})
    def test_extract_context_when_b3_format_is_valid_and_baggage_invalid(self):
        extracted_context = self.composite_propagator_b3_baggage_object.extract_context()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(extracted_context)
        self.assertEqual(traceid , '8128c50fd8653b5d98fea4de58eca772')
        self.assertEqual(spanid , '136eec09c948be26')
        self.assertEqual(sampled , 1)
        val = baggage.get_all(extracted_context)
        self.assertEqual(val , {'': 'value1'})

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c50fd8653b5d98fea4de58eca772"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136eec09c"})
    @mock.patch.dict(os.environ, {"x-b3-sampled": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd8653b5d98fea4de58eca772-136eec09c-01"})
    @mock.patch.dict(os.environ, {"baggage": "key1=value1,key2=value2"})
    def test_extract_context_when_baggage_is_valid_but_b3_spanid_is_invalid(self):
        extracted_context = self.composite_propagator_b3_baggage_object.extract_context()
        self.assertEqual(baggage.get_all(extracted_context) , {'key1':'value1', 'key2':'value2'})

    @mock.patch.dict(os.environ, {"x-b3-traceid": "98fea4de58eca772"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136eec09c948be26"})
    @mock.patch.dict(os.environ, {"x-b3-sampled": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    @mock.patch.dict(os.environ, {"traceparent": "00-000000000000000098fea4de58eca772-136eec09c948be26-01"})
    @mock.patch.dict(os.environ, {"baggage": "key1=value1,key2=value2"})
    def test_extract_context_when_baggage_is_valid_and_traceid_of_b3_has_16_hex_char(self):
        extracted_context = self.composite_propagator_b3_baggage_object.extract_context()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(extracted_context)
        self.assertEqual(traceid , '000000000000000098fea4de58eca772')
        self.assertEqual(spanid , '136eec09c948be26')
        self.assertEqual(sampled , 1)
        val1 = baggage.get_baggage("key1", extracted_context)
        val2 = baggage.get_baggage("key2", extracted_context)
        self.assertEqual(val1 , "value1")
        self.assertEqual(val2 , "value2")

    @mock.patch.dict(os.environ, {"x-b3-traceid": "98fea"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136eec09c948be26"})
    @mock.patch.dict(os.environ, {"x-b3-sampled": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd8653b5d98fea4de56a789da-136eec09c948be27-01"})
    def test_extract_context_when_b3_traceid_is_invalid(self):
        extracted_context = self.composite_propagator_b3_baggage_object.extract_context()
        self.assertEqual(extracted_context , {})

    @mock.patch.dict(os.environ, {"x-b3-traceid": "98fea"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136eec09c"})
    @mock.patch.dict(os.environ, {"x-b3-sampled": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd8653b5d98fea4de-136eec09c-01"})
    def test_extract_context_when_b3_traceid_and_spanid_are_invalid(self):
        extracted_context = self.composite_propagator_b3_baggage_object.extract_context()
        self.assertEqual(extracted_context , {})

    @mock.patch.dict(os.environ, {"x-b3-traceid": "8128c50fd8653b5d98fea4de58eca772"})
    @mock.patch.dict(os.environ, {"x-b3-spanid": "136eec09c948be26"})
    @mock.patch.dict(os.environ, {"x-b3-sampled": "1"})
    @mock.patch.dict(os.environ, {"x-b3-parentspanid": "e28bf981e15deb7f"})
    @mock.patch.dict(os.environ, {"traceparent": "00-8128c50fd8653b5d98fea4de58eca772-136eec09c948be26-01"})
    @mock.patch.dict(os.environ, {"baggage": "key1=value1,=value2"})
    def test_extract_context_when_a_baggage_key_is_not_passed(self):
        extracted_context = self.composite_propagator_b3_baggage_object.extract_context()
        traceid, spanid, sampled, parentspanid, tracestate = get_details_from_context(extracted_context)
        self.assertEqual(traceid , '8128c50fd8653b5d98fea4de58eca772')
        self.assertEqual(spanid , '136eec09c948be26')
        self.assertEqual(sampled , 1)
        self.assertEqual(baggage.get_all(extracted_context), {'key1':'value1', '':'value2'})

    @mock.patch.dict(os.environ, {"baggage": "example1-value1;example2-value2"})
    def test_extract_context_baggage_invalid_format(self):
        extracted_context = self.composite_propagator_b3_baggage_object.extract_context()
        val1 = baggage.get_baggage("example1", extracted_context)
        val2 = baggage.get_baggage("example2", extracted_context)
        self.assertNotEqual(val1 , "value1")
        self.assertNotEqual(val2 , "value2")
        self.assertIsNone(val1)
        self.assertIsNone(val2)

    @mock.patch.dict(os.environ, {"baggage": "example1=value1%2Cvalue2,example2=value3%2Cvalue4"})
    def test_extract_context_when_baggage_with_valid_format_has_commas_in_values(self):
        extracted_context = self.composite_propagator_b3_baggage_object.extract_context()
        val1 = baggage.get_baggage("example1", extracted_context)
        val2 = baggage.get_baggage("example2", extracted_context)
        self.assertEqual(val1 , "value1,value2")
        self.assertEqual(val2 , "value3,value4")
