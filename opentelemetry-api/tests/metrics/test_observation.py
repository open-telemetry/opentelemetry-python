# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase

from opentelemetry.metrics import Observation


class TestObservation(TestCase):
    def test_measurement_init(self):
        try:
            # int
            Observation(321, {"hello": "world"})

            # float
            Observation(321.321, {"hello": "world"})
        except Exception:  # pylint: disable=broad-exception-caught
            self.fail(
                "Unexpected exception raised when instantiating Observation"
            )

    def test_measurement_equality(self):
        self.assertEqual(
            Observation(321, {"hello": "world"}),
            Observation(321, {"hello": "world"}),
        )

        self.assertNotEqual(
            Observation(321, {"hello": "world"}),
            Observation(321.321, {"hello": "world"}),
        )
        self.assertNotEqual(
            Observation(321, {"baz": "world"}),
            Observation(321, {"hello": "world"}),
        )
