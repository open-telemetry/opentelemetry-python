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

import unittest
from unittest.mock import patch

from opentelemetry import context

from .base_context import ContextTestCases

try:
    import contextvars  # pylint: disable=unused-import
    from opentelemetry.context.contextvars_context import (
        ContextVarsRuntimeContext,
    )
except ImportError:
    raise unittest.SkipTest("contextvars not available")


class TestContextVarsContext(ContextTestCases.BaseTest):
    def setUp(self) -> None:
        super(TestContextVarsContext, self).setUp()
        self.mock_runtime = patch.object(
            context, "_RUNTIME_CONTEXT", ContextVarsRuntimeContext(),
        )
        self.mock_runtime.start()

    def tearDown(self) -> None:
        super(TestContextVarsContext, self).tearDown()
        self.mock_runtime.stop()
