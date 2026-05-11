# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
#
# type: ignore

from unittest import TestCase

from opentelemetry.baggage import get_baggage, set_baggage
from opentelemetry.baggage.propagation import W3CBaggagePropagator


class TestBaggageManager(TestCase):
    def test_propagate_baggage(self):
        carrier = {}
        propagator = W3CBaggagePropagator()

        ctx = set_baggage("Test1", "value1")
        ctx = set_baggage("test2", "value2", context=ctx)

        propagator.inject(carrier, ctx)
        ctx_propagated = propagator.extract(carrier)

        self.assertEqual(
            get_baggage("Test1", context=ctx_propagated), "value1"
        )
        self.assertEqual(
            get_baggage("test2", context=ctx_propagated), "value2"
        )
