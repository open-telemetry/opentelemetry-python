# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from opentelemetry.profiles.context._rs import sum_as_string


def test_sum_as_string():
    assert sum_as_string(1, 2) == "3"
