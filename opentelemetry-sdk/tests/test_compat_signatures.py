# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import unittest

from opentelemetry.sdk._logs import Logger, LoggerProvider
from opentelemetry.sdk.metrics import Meter, MeterProvider
from opentelemetry.sdk.trace import Tracer, TracerProvider


class TestSdkImplementationsNotWrapped(unittest.TestCase):
    """The SDK's API implementations accept ``**_kwargs`` and so skip the compat wrapper."""

    def test_not_wrapped(self) -> None:
        cases: list[tuple[type, str]] = [
            (TracerProvider, "get_tracer"),
            (Tracer, "start_span"),
            (Tracer, "start_as_current_span"),
            (MeterProvider, "get_meter"),
            (Meter, "create_counter"),
            (Meter, "create_up_down_counter"),
            (Meter, "create_observable_counter"),
            (Meter, "create_histogram"),
            (Meter, "create_gauge"),
            (Meter, "create_observable_gauge"),
            (Meter, "create_observable_up_down_counter"),
            (LoggerProvider, "get_logger"),
            (Logger, "emit"),
            (Logger, "enabled"),
        ]
        for cls, name in cases:
            with self.subTest(cls=cls.__qualname__, method=name):
                self.assertFalse(getattr(cls, name).__code__.co_filename.startswith("<compat "))
