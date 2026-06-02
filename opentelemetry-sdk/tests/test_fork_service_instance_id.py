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

# pylint: disable=protected-access

import multiprocessing
import os
import unittest
from platform import system

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_INSTANCE_ID
from opentelemetry.sdk.trace import TracerProvider

_fork_ctx = (
    multiprocessing.get_context("fork") if system() != "Windows" else None
)


def _instance_id(provider):
    resource = (
        provider._sdk_config.resource
        if isinstance(provider, MeterProvider)
        else provider._resource
    )
    return resource.attributes.get(SERVICE_INSTANCE_ID)


@unittest.skipUnless(hasattr(os, "fork"), "needs *nix")
class TestForkServiceInstanceId(unittest.TestCase):
    def test_meter_and_tracer_share_instance_id_after_fork(self):
        """Both providers must report the SAME, fresh id in a forked worker."""
        meter_provider = MeterProvider()
        tracer_provider = TracerProvider()

        parent_id = _instance_id(meter_provider)
        # Before forking, both providers already share the default id.
        self.assertEqual(parent_id, _instance_id(tracer_provider))

        def child(conn):
            conn.send(
                (
                    _instance_id(meter_provider),
                    _instance_id(tracer_provider),
                )
            )
            conn.close()

        parent_conn, child_conn = _fork_ctx.Pipe()
        process = _fork_ctx.Process(target=child, args=(child_conn,))
        process.start()
        child_meter_id, child_tracer_id = parent_conn.recv()
        process.join()

        # Same id across signals, unique at the instance level.
        self.assertEqual(child_meter_id, child_tracer_id)
        self.assertNotEqual(child_meter_id, parent_id)

    def test_provider_created_after_fork_adopts_child_id(self):
        """A provider built post-fork must adopt the child's shared id."""
        meter_provider = MeterProvider()
        parent_id = _instance_id(meter_provider)

        def child(conn):
            # Created only in the child, after the fork hook has run.
            late_tracer_provider = TracerProvider()
            conn.send(
                (
                    _instance_id(meter_provider),
                    _instance_id(late_tracer_provider),
                )
            )
            conn.close()

        parent_conn, child_conn = _fork_ctx.Pipe()
        process = _fork_ctx.Process(target=child, args=(child_conn,))
        process.start()
        forked_meter_id, late_tracer_id = parent_conn.recv()
        process.join()

        self.assertEqual(forked_meter_id, late_tracer_id)
        self.assertNotEqual(late_tracer_id, parent_id)
