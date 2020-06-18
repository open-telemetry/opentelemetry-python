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

import unittest
from unittest.mock import Mock

from opentelemetry.propagators.composite import CompositeHTTPPropagator


def get_as_list(dict_object, key):
    value = dict_object.get(key)
    return [value] if value is not None else []


def mock_inject(name, value="data"):
    def wrapped(setter, carrier=None, context=None):
        carrier[name] = value

    return wrapped


def mock_extract(name, value="context"):
    def wrapped(getter, carrier=None, context=None):
        new_context = context.copy()
        new_context[name] = value
        return new_context

    return wrapped


class TestCompositePropagator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_propagator_0 = Mock(
            inject=mock_inject("mock-0"), extract=mock_extract("mock-0")
        )
        cls.mock_propagator_1 = Mock(
            inject=mock_inject("mock-1"), extract=mock_extract("mock-1")
        )
        cls.mock_propagator_2 = Mock(
            inject=mock_inject("mock-0", value="data2"),
            extract=mock_extract("mock-0", value="context2"),
        )

    def test_no_propagators(self):
        propagator = CompositeHTTPPropagator([])
        new_carrier = {}
        propagator.inject(dict.__setitem__, carrier=new_carrier)
        self.assertEqual(new_carrier, {})

        context = propagator.extract(
            get_as_list, carrier=new_carrier, context={}
        )
        self.assertEqual(context, {})

    def test_single_propagator(self):
        propagator = CompositeHTTPPropagator([self.mock_propagator_0])

        new_carrier = {}
        propagator.inject(dict.__setitem__, carrier=new_carrier)
        self.assertEqual(new_carrier, {"mock-0": "data"})

        context = propagator.extract(
            get_as_list, carrier=new_carrier, context={}
        )
        self.assertEqual(context, {"mock-0": "context"})

    def test_multiple_propagators(self):
        propagator = CompositeHTTPPropagator(
            [self.mock_propagator_0, self.mock_propagator_1]
        )

        new_carrier = {}
        propagator.inject(dict.__setitem__, carrier=new_carrier)
        self.assertEqual(new_carrier, {"mock-0": "data", "mock-1": "data"})

        context = propagator.extract(
            get_as_list, carrier=new_carrier, context={}
        )
        self.assertEqual(context, {"mock-0": "context", "mock-1": "context"})

    def test_multiple_propagators_same_key(self):
        # test that when multiple propagators extract/inject the same
        # key, the later propagator values are extracted/injected
        propagator = CompositeHTTPPropagator(
            [self.mock_propagator_0, self.mock_propagator_2]
        )

        new_carrier = {}
        propagator.inject(dict.__setitem__, carrier=new_carrier)
        self.assertEqual(new_carrier, {"mock-0": "data2"})

        context = propagator.extract(
            get_as_list, carrier=new_carrier, context={}
        )
        self.assertEqual(context, {"mock-0": "context2"})
