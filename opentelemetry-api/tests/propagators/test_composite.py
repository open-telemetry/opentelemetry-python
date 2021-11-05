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

# type: ignore

import unittest
from unittest.mock import Mock

from opentelemetry.propagators.composite import CompositePropagator


def get_as_list(dict_object, key):
    value = dict_object.get(key)
    return [value] if value is not None else []


def mock_inject(name, value="data"):
    def wrapped(carrier=None, context=None, setter=None):
        carrier[name] = value
        setter.set({}, f"inject_field_{name}_0", None)
        setter.set({}, f"inject_field_{name}_1", None)

    return wrapped


def mock_extract(name, value="context"):
    def wrapped(carrier=None, context=None, getter=None):
        new_context = context.copy()
        new_context[name] = value
        return new_context

    return wrapped


def mock_fields(name):
    return {f"inject_field_{name}_0", f"inject_field_{name}_1"}


class TestCompositePropagator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_propagator_0 = Mock(
            inject=mock_inject("mock-0"),
            extract=mock_extract("mock-0"),
            fields=mock_fields("mock-0"),
        )
        cls.mock_propagator_1 = Mock(
            inject=mock_inject("mock-1"),
            extract=mock_extract("mock-1"),
            fields=mock_fields("mock-1"),
        )
        cls.mock_propagator_2 = Mock(
            inject=mock_inject("mock-0", value="data2"),
            extract=mock_extract("mock-0", value="context2"),
            fields=mock_fields("mock-0"),
        )

    def test_no_propagators(self):
        propagator = CompositePropagator([])
        new_carrier = {}
        propagator.inject(new_carrier)
        self.assertEqual(new_carrier, {})

        context = propagator.extract(
            carrier=new_carrier, context={}, getter=get_as_list
        )
        self.assertEqual(context, {})

    def test_single_propagator(self):
        propagator = CompositePropagator([self.mock_propagator_0])

        new_carrier = {}
        propagator.inject(new_carrier)
        self.assertEqual(new_carrier, {"mock-0": "data"})

        context = propagator.extract(
            carrier=new_carrier, context={}, getter=get_as_list
        )
        self.assertEqual(context, {"mock-0": "context"})

    def test_multiple_propagators(self):
        propagator = CompositePropagator(
            [self.mock_propagator_0, self.mock_propagator_1]
        )

        new_carrier = {}
        propagator.inject(new_carrier)
        self.assertEqual(new_carrier, {"mock-0": "data", "mock-1": "data"})

        context = propagator.extract(
            carrier=new_carrier, context={}, getter=get_as_list
        )
        self.assertEqual(context, {"mock-0": "context", "mock-1": "context"})

    def test_multiple_propagators_same_key(self):
        # test that when multiple propagators extract/inject the same
        # key, the later propagator values are extracted/injected
        propagator = CompositePropagator(
            [self.mock_propagator_0, self.mock_propagator_2]
        )

        new_carrier = {}
        propagator.inject(new_carrier)
        self.assertEqual(new_carrier, {"mock-0": "data2"})

        context = propagator.extract(
            carrier=new_carrier, context={}, getter=get_as_list
        )
        self.assertEqual(context, {"mock-0": "context2"})

    def test_fields(self):
        propagator = CompositePropagator(
            [
                self.mock_propagator_0,
                self.mock_propagator_1,
                self.mock_propagator_2,
            ]
        )

        mock_setter = Mock()

        propagator.inject({}, setter=mock_setter)

        inject_fields = set()

        for mock_call in mock_setter.mock_calls:
            inject_fields.add(mock_call[1][1])

        self.assertEqual(inject_fields, propagator.fields)
