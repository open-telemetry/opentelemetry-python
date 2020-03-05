# Copyright 2020, OpenTelemetry Authors
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
from logging import ERROR
from unittest.mock import Mock

from opentelemetry.propagators.composite import CompositePropagator


def get_as_list(dict_object, key):
    value = dict_object.get(key)
    return [value] if value is not None else []


def mock_inject(name):
    def wrapped(setter, carrier=None, context=None):
        carrier[name] = "data"

    return wrapped


def mock_extract(name):
    def wrapped(getter, carrier=None, context=None):
        context[name] = "context"
        return context

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

        def mock_broken_extract(getter, carrier=None, context=None):
            raise Exception("failed to extract")

        def mock_broken_inject(setter, carrier=None, context=None):
            raise Exception("failed to inject")

        cls.mock_broken_extract = Mock(
            inject=mock_inject("mock-broken-extract"),
            extract=mock_broken_extract,
        )
        cls.mock_broken_inject = Mock(
            inject=mock_broken_inject,
            extract=mock_extract("mock-broken-inject"),
        )

    def test_no_propagators(self):
        CompositePropagator.propagators = []
        new_carrier = {}
        CompositePropagator.inject(dict.__setitem__, carrier=new_carrier)
        self.assertEqual(new_carrier, {})
        CompositePropagator.extract(get_as_list, carrier=new_carrier)
        self.assertEqual(new_carrier, {})

    def test_single_propagator(self):
        new_carrier = {}
        CompositePropagator.propagators = [self.mock_propagator_0]
        CompositePropagator.inject(dict.__setitem__, carrier=new_carrier)
        self.assertEqual(new_carrier, {"mock-0": "data"})

        context = {}
        CompositePropagator.extract(
            get_as_list, carrier=new_carrier, context=context
        )
        self.assertEqual(context, {"mock-0": "context"})

    def test_multiple_propagators(self):
        CompositePropagator.propagators = [
            self.mock_propagator_0,
            self.mock_propagator_1,
        ]

        new_carrier = {}
        CompositePropagator.inject(dict.__setitem__, carrier=new_carrier)
        self.assertEqual(new_carrier, {"mock-0": "data", "mock-1": "data"})

        context = {}
        CompositePropagator.extract(
            get_as_list, carrier=new_carrier, context=context
        )
        self.assertEqual(context, {"mock-0": "context", "mock-1": "context"})

    def test_broken_propagator(self):
        CompositePropagator.propagators = [
            self.mock_broken_extract,
            self.mock_broken_inject,
        ]

        new_carrier = {}
        with self.assertLogs(level=ERROR):
            CompositePropagator.inject(dict.__setitem__, carrier=new_carrier)
        self.assertEqual(new_carrier, {"mock-broken-extract": "data"})

        context = {}
        with self.assertLogs(level=ERROR):
            CompositePropagator.extract(
                get_as_list, carrier=new_carrier, context=context
            )
        self.assertEqual(context, {"mock-broken-inject": "context"})
