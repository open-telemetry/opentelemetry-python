# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import random
from collections.abc import Iterator
from os import environ
from threading import Thread
from threading import enumerate as enumerate_threads
from time import monotonic, sleep

import pytest

from opentelemetry.environment_variables import OTEL_PYTHON_CONTEXT

# PeriodicExportingMetricReader names its ticker thread this. The name is
# hardcoded, so every instance shares it.
METRIC_READER_THREAD_NAME = "OtelPeriodicExportingMetricReader"

# shutdown() joins the ticker with a timeout, so a thread that is on its way
# out can still be alive for a moment after the test body returns. Wait this
# long before calling it a leak. Only a test that actually leaks pays the cost.
_LEAK_GRACE_PERIOD_SECONDS = 2.0
_LEAK_POLL_INTERVAL_SECONDS = 0.05


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


def live_metric_reader_threads() -> set[Thread]:
    return {thread for thread in enumerate_threads() if thread.name == METRIC_READER_THREAD_NAME}


@pytest.fixture(autouse=True)
def no_leaked_metric_reader_threads(request: pytest.FixtureRequest) -> Iterator[None]:
    """Fail a test that leaves a PeriodicExportingMetricReader ticker thread running.

    The ticker is a daemon thread, so nothing reaps it between tests. A leaked
    one keeps waking up and calling collect() for the rest of the session,
    inside unrelated tests. That has produced cross-test failures before, see
    issue #5157.

    Only threads that appear during this test are reported, so one leak fails
    the test that caused it rather than every test that runs after it.
    """
    before = live_metric_reader_threads()

    yield

    leaked = live_metric_reader_threads() - before
    deadline = monotonic() + _LEAK_GRACE_PERIOD_SECONDS
    while leaked and monotonic() < deadline:
        sleep(_LEAK_POLL_INTERVAL_SECONDS)
        leaked = live_metric_reader_threads() - before

    if leaked:
        pytest.fail(
            f"{request.node.nodeid} left {len(leaked)} {METRIC_READER_THREAD_NAME} "
            "thread(s) running. A leaked ticker thread calls collect() during "
            "later tests and can fail them (see issue #5157). Shut the reader "
            "down, or its MeterProvider, from a finally block or addCleanup so "
            "it happens even when the test fails."
        )
