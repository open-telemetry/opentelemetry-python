# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import patch

from opentelemetry import context
from opentelemetry.context.contextvars_context import ContextVarsRuntimeContext

# pylint: disable=import-error,no-name-in-module
from tests.context.base_context import ContextTestCases


class TestContextVarsContext(ContextTestCases.BaseTest):
    # pylint: disable=invalid-name
    def setUp(self) -> None:
        super().setUp()
        self.mock_runtime = patch.object(
            context,
            "_RUNTIME_CONTEXT",
            ContextVarsRuntimeContext(),
        )
        self.mock_runtime.start()

    # pylint: disable=invalid-name
    def tearDown(self) -> None:
        super().tearDown()
        self.mock_runtime.stop()
