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
from opentelemetry.sdk.resources import Resource

_fork_ctx = (
    multiprocessing.get_context("fork") if system() != "Windows" else None
)


@unittest.skipUnless(
    hasattr(os, "fork"),
    "needs *nix",
)
class TestMeterProviderFork(unittest.TestCase):
    def test_at_fork_reinit_changes_service_instance_id(self):
        """_at_fork_reinit should assign a new service.instance.id."""
        resource = Resource({"service.instance.id": "original-id"})
        provider = MeterProvider(resource=resource)

        original_id = provider._sdk_config.resource.attributes.get(
            "service.instance.id"
        )
        self.assertEqual(original_id, "original-id")

        provider._at_fork_reinit()

        new_id = provider._sdk_config.resource.attributes.get(
            "service.instance.id"
        )
        self.assertNotEqual(new_id, "original-id")
        self.assertIsNotNone(new_id)

    def test_at_fork_reinit_preserves_other_resource_attributes(self):
        """_at_fork_reinit should not affect other resource attributes."""
        resource = Resource(
            {
                "service.name": "my-service",
                "service.instance.id": "original-id",
                "deployment.environment": "production",
            }
        )
        provider = MeterProvider(resource=resource)

        provider._at_fork_reinit()

        attrs = provider._sdk_config.resource.attributes
        self.assertEqual(attrs.get("service.name"), "my-service")
        self.assertEqual(attrs.get("deployment.environment"), "production")

    def test_fork_produces_unique_service_instance_ids(self):
        """Each forked worker should get a distinct service.instance.id."""
        provider = MeterProvider()

        parent_id = provider._sdk_config.resource.attributes.get(
            "service.instance.id"
        )
        self.assertIsNotNone(parent_id)

        def child(conn):
            child_id = provider._sdk_config.resource.attributes.get(
                "service.instance.id"
            )
            conn.send(child_id)
            conn.close()

        parent_conn, child_conn = _fork_ctx.Pipe()
        process = _fork_ctx.Process(target=child, args=(child_conn,))
        process.start()
        child_id = parent_conn.recv()
        process.join()

        # Child should have a different service.instance.id than parent
        self.assertNotEqual(parent_id, child_id)
        self.assertIsNotNone(child_id)

    def test_multiple_forks_produce_unique_service_instance_ids(self):
        """Each of N forked workers should have a distinct service.instance.id."""
        provider = MeterProvider()

        def child(conn):
            child_id = provider._sdk_config.resource.attributes.get(
                "service.instance.id"
            )
            conn.send(child_id)
            conn.close()

        ids = set()
        processes = []
        conns = []

        for _ in range(4):
            parent_conn, child_conn = _fork_ctx.Pipe()
            process = _fork_ctx.Process(target=child, args=(child_conn,))
            processes.append(process)
            conns.append(parent_conn)
            process.start()

        for conn in conns:
            ids.add(conn.recv())

        for process in processes:
            process.join()

        # All 4 workers should have distinct IDs
        self.assertEqual(len(ids), 4)
