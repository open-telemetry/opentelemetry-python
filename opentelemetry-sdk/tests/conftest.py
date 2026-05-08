# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import random
from os import environ

import pytest

from opentelemetry.environment_variables import OTEL_PYTHON_CONTEXT


def pytest_sessionstart(session):
    # pylint: disable=unused-argument
    environ[OTEL_PYTHON_CONTEXT] = "contextvars_context"


def pytest_sessionfinish(session):
    # pylint: disable=unused-argument
    environ.pop(OTEL_PYTHON_CONTEXT)


@pytest.fixture(autouse=True)
def random_seed():
    # We use random numbers a lot in sampling tests, make sure they are always the same.
    random.seed(0)
