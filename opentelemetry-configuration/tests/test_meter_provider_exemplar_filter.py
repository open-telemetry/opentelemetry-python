# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Tests access private members of SDK classes to assert correct configuration.
# pylint: disable=protected-access

import unittest

from opentelemetry.configuration._meter_provider import (
    create_meter_provider,
)
from opentelemetry.configuration.models import (
    ExemplarFilter as ExemplarFilterConfig,
)
from opentelemetry.configuration.models import (
    MeterProvider as MeterProviderConfig,
)
from opentelemetry.sdk.metrics import (
    AlwaysOffExemplarFilter,
    AlwaysOnExemplarFilter,
    TraceBasedExemplarFilter,
)


class TestExemplarFilter(unittest.TestCase):
    @staticmethod
    def _make_config(exemplar_filter):
        return MeterProviderConfig(readers=[], exemplar_filter=exemplar_filter)

    def test_always_on(self):
        provider = create_meter_provider(
            self._make_config(ExemplarFilterConfig.always_on)
        )
        self.assertIsInstance(
            provider._sdk_config.exemplar_filter, AlwaysOnExemplarFilter
        )

    def test_always_off(self):
        provider = create_meter_provider(
            self._make_config(ExemplarFilterConfig.always_off)
        )
        self.assertIsInstance(
            provider._sdk_config.exemplar_filter, AlwaysOffExemplarFilter
        )

    def test_trace_based(self):
        provider = create_meter_provider(
            self._make_config(ExemplarFilterConfig.trace_based)
        )
        self.assertIsInstance(
            provider._sdk_config.exemplar_filter, TraceBasedExemplarFilter
        )

    def test_absent_defaults_to_trace_based(self):
        provider = create_meter_provider(MeterProviderConfig(readers=[]))
        self.assertIsInstance(
            provider._sdk_config.exemplar_filter, TraceBasedExemplarFilter
        )
