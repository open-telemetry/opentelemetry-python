# Copyright 2019, OpenTelemetry Authors
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

from opentelemetry import distributedcontext as dctx_api
from opentelemetry.sdk import distributedcontext


class TestDistributedContextManager(unittest.TestCase):
    def setUp(self):
        self.manager = distributedcontext.DistributedContextManager()

    def test_use_context(self):
        # Context is None initially
        self.assertIsNone(self.manager.get_current_context())

        # Start initial context
        dctx = dctx_api.DistributedContext(())
        with self.manager.use_context(dctx) as current:
            self.assertIs(current, dctx)
            self.assertIs(
                self.manager.get_current_context(),
                dctx,
            )

            # Context is overridden
            nested_dctx = dctx_api.DistributedContext(())
            with self.manager.use_context(nested_dctx) as current:
                self.assertIs(current, nested_dctx)
                self.assertIs(
                    self.manager.get_current_context(),
                    nested_dctx,
                )

            # Context is restored
            self.assertIs(
                self.manager.get_current_context(),
                dctx,
            )
