# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import struct
import subprocess
import sys
import textwrap
import unittest

from opentelemetry.process_context import (
    publish_context,
    unpublish_context,
    update_context,
)
from opentelemetry.sdk.resources import Resource


class TestPublishContext(unittest.TestCase):
    def tearDown(self):
        try:
            unpublish_context()
        except RuntimeError:
            pass

    def test_publish_context_lifecycle(self):
        resource = Resource(
            {"service.name": "test", "version": 1, "pi": 3.14, "active": True}
        )
        self.assertIsNone(publish_context(resource))

        with self.assertRaises(RuntimeError):
            publish_context(resource)

        self.assertIsNone(update_context(resource))
        self.assertIsNone(update_context(resource))

        self.assertIsNone(unpublish_context())
        self.assertIsNone(publish_context(resource))

    def test_update_before_publish_raises(self):
        with self.assertRaises(RuntimeError):
            update_context(Resource({}))

    def test_unpublish_before_publish_raises(self):
        with self.assertRaises(RuntimeError):
            unpublish_context()

    def test_cross_process_memory_region(self):
        """Spawn a child that publishes a fixed context; read and validate its memory region."""
        child_script = textwrap.dedent("""\
            import sys
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.process_context._rs import publish_context

            resource = Resource({"service.name": "otel-test-service", "version": 42})
            publish_context(resource)

            sys.stdout.write("ready\\n")
            sys.stdout.flush()
            sys.stdin.readline()
        """)

        # pylint: disable-next=consider-using-with
        proc = subprocess.Popen(
            [sys.executable, "-c", child_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        try:
            self.assertEqual(proc.stdout.readline(), b"ready\n")

            pid = proc.pid

            # Locate the OTEL_CTX mapping and verify the memfd name.
            start_addr = None
            with open(f"/proc/{pid}/maps", encoding="utf-8") as maps_file:
                for maps_line in maps_file:
                    if "OTEL_CTX" in maps_line:
                        start_addr = int(maps_line.split("-")[0], 16)
                        self.assertIn(":OTEL_CTX", maps_line)
                        break

            self.assertIsNotNone(
                start_addr,
                f"OTEL_CTX mapping not found in /proc/{pid}/maps",
            )

            # Read the 32-byte header and the variable-length payload in one
            # open so there is no TOCTOU window between the two reads.
            with open(f"/proc/{pid}/mem", "rb") as mem:
                mem.seek(start_addr)
                header_bytes = mem.read(32)

                signature = header_bytes[0:8]
                version = struct.unpack_from("<I", header_bytes, 8)[0]
                payload_size = struct.unpack_from("<I", header_bytes, 12)[0]
                timestamp_ns = struct.unpack_from("<Q", header_bytes, 16)[0]
                payload_ptr = struct.unpack_from("<Q", header_bytes, 24)[0]

                mem.seek(payload_ptr)
                payload_bytes = mem.read(payload_size)

            self.assertEqual(signature, b"OTEL_CTX")
            self.assertEqual(version, 2)
            self.assertGreater(payload_size, 0)
            self.assertGreater(timestamp_ns, 0)
            self.assertNotEqual(payload_ptr, 0)

            # Protobuf string fields are length-prefixed raw UTF-8, so the
            # attribute key and value appear verbatim in the serialised payload.
            self.assertIn(b"service.name", payload_bytes)
            self.assertIn(b"otel-test-service", payload_bytes)

        finally:
            proc.stdin.write(b"\n")
            proc.stdin.flush()
            proc.wait()
