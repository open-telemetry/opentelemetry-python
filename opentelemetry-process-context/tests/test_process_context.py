# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import struct
import subprocess
import sys
import threading
import unittest
from pathlib import Path

from opentelemetry.process_context import (
    publish_context,
    unpublish_context,
)
from opentelemetry.sdk.resources import Resource

HEADER_SIZE = 32

# Helper scripts (see tests/scripts/).
_SCRIPTS_DIR = Path(__file__).parent / "scripts"


def _script_cmd(name: str) -> list[str]:
    """Build the command to run a helper script under the current interpreter."""
    return [sys.executable, str(_SCRIPTS_DIR / name)]


def _read_header(pid: int, addr: int) -> dict:
    with open(f"/proc/{pid}/mem", "rb") as mem:
        mem.seek(addr)
        header_bytes = mem.read(HEADER_SIZE)

        payload_size = struct.unpack_from("<I", header_bytes, 12)[0]
        payload_ptr = struct.unpack_from("<Q", header_bytes, 24)[0]

        mem.seek(payload_ptr)
        payload_bytes = mem.read(payload_size)

    return {
        "signature": header_bytes[0:8],
        "version": struct.unpack_from("<I", header_bytes, 8)[0],
        "payload_size": payload_size,
        "timestamp_ns": struct.unpack_from("<Q", header_bytes, 16)[0],
        "payload_ptr": payload_ptr,
        "payload": payload_bytes,
    }


def _find_otel_ctx_addr(pid: int) -> int | None:
    with open(f"/proc/{pid}/maps", encoding="utf-8") as maps_file:
        for maps_line in maps_file:
            if ":OTEL_CTX" in maps_line:
                return int(maps_line.split("-")[0], 16)
    return None


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
        self.assertIsNone(publish_context(resource))
        self.assertIsNone(publish_context(resource))

        self.assertIsNone(unpublish_context())
        self.assertIsNone(publish_context(resource))

    def test_publish_context_with_attributes(self):
        resource = Resource({"service.name": "test"})
        self.assertIsNone(
            publish_context(resource, {"deployment.environment": "prod"})
        )
        self.assertIsNone(
            publish_context(resource, {"k": 1, "nested": {"a": 2}})
        )
        self.assertIsNone(publish_context(resource))

    def test_unpublish_before_publish_raises(self):
        with self.assertRaises(RuntimeError):
            unpublish_context()

    def test_concurrent_publish(self):
        """Many threads publishing concurrently must not crash or error."""
        thread_count = 8
        iterations = 200
        barrier = threading.Barrier(thread_count)
        errors: list[BaseException] = []

        def worker(index: int) -> None:
            resource = Resource(
                {"service.name": f"svc-{index}", "version": index}
            )
            barrier.wait()
            try:
                for _ in range(iterations):
                    publish_context(resource)
            # pylint: disable-next=broad-except
            except BaseException as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=worker, args=(i,))
            for i in range(thread_count)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])
        # The mapping is still in a consistent, usable state.
        self.assertIsNone(publish_context(Resource({"service.name": "final"})))
        self.assertIsNone(unpublish_context())

    @unittest.skipUnless(hasattr(os, "fork"), "requires os.fork")
    def test_publish_in_forked_child(self):
        """A child that re-publishes after fork must not crash and the parent
        must remain unaffected."""
        result = subprocess.run(_script_cmd("fork_republish.py"), check=False)
        self.assertEqual(
            result.returncode,
            0,
            "fork/re-publish script did not exit cleanly",
        )

    @unittest.skipUnless(hasattr(os, "fork"), "requires os.fork")
    def test_unpublish_in_forked_child_without_publish(self):
        """A child that inherits the parent's region but never publishes must
        get NotPublished from unpublish (not a crash), and the parent stays
        usable."""
        result = subprocess.run(
            _script_cmd("fork_unpublish_without_publish.py"), check=False
        )
        self.assertEqual(
            result.returncode,
            0,
            "fork/unpublish-without-publish script did not exit cleanly",
        )

    @unittest.skipUnless(
        sys.platform.startswith("linux"), "requires /proc/<pid>/{maps,mem}"
    )
    def test_cross_process_memory_region(self):
        """Spawn a child that publishes a fixed context and read/validate its memory region."""
        with subprocess.Popen(
            _script_cmd("publish_and_wait.py"),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        ) as proc:
            self.assertEqual(proc.stdout.readline(), b"ready\n")

            start_addr = _find_otel_ctx_addr(proc.pid)
            self.assertIsNotNone(
                start_addr,
                f"OTEL_CTX mapping not found in /proc/{proc.pid}/maps",
            )

            header = _read_header(proc.pid, start_addr)

            self.assertEqual(header["signature"], b"OTEL_CTX")
            self.assertEqual(header["version"], 2)
            self.assertGreater(header["payload_size"], 0)
            self.assertGreater(header["timestamp_ns"], 0)
            self.assertNotEqual(header["payload_ptr"], 0)
            self.assertIn(b"service.name", header["payload"])
            self.assertIn(b"otel-test-service", header["payload"])
            self.assertIn(b"deployment.environment", header["payload"])
            self.assertIn(b"otel-test-env", header["payload"])

    @unittest.skipUnless(
        sys.platform.startswith("linux"), "requires /proc/<pid>/{maps,mem}"
    )
    def test_mapping_present_in_parent_absent_in_child(self):
        """After a fork the mapping must be visible in the parent but stripped
        from the child (MADV_DONTFORK)."""
        with subprocess.Popen(
            _script_cmd("fork_keepalive.py"),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        ) as proc:
            parent_pid, child_pid = (
                int(token) for token in proc.stdout.readline().split()
            )

            # Parent: mapping present in /proc/maps and readable via /proc/mem.
            parent_addr = _find_otel_ctx_addr(parent_pid)
            self.assertIsNotNone(
                parent_addr,
                "OTEL_CTX mapping missing from the parent",
            )
            header = _read_header(parent_pid, parent_addr)
            self.assertEqual(header["signature"], b"OTEL_CTX")
            self.assertEqual(header["version"], 2)

            # Child: mapping absent from /proc/maps...
            self.assertIsNone(
                _find_otel_ctx_addr(child_pid),
                "OTEL_CTX mapping leaked into the forked child",
            )
            # The parent's address is unmapped in the child, so reading
            # it from /proc/<child>/mem fails.
            with self.assertRaises(OSError):
                with open(f"/proc/{child_pid}/mem", "rb") as mem:
                    mem.seek(parent_addr)
                    mem.read(HEADER_SIZE)

    @unittest.skipUnless(
        sys.platform.startswith("linux"), "requires /proc/<pid>/{maps,mem}"
    )
    def test_update_in_place_keeps_stable_mapping(self):
        """An update reuses the same header mapping, advances the
        timestamp and swaps in the new payload."""
        with subprocess.Popen(
            _script_cmd("publisher.py"),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        ) as proc:
            pid = int(proc.stdout.readline())

            addr1 = _find_otel_ctx_addr(pid)
            self.assertIsNotNone(addr1)
            before = _read_header(pid, addr1)
            self.assertIn(b"otel-first", before["payload"])

            proc.stdin.write("update\n")
            proc.stdin.flush()
            self.assertEqual(proc.stdout.readline(), "done\n")

            addr2 = _find_otel_ctx_addr(pid)
            self.assertEqual(
                addr2, addr1, "header mapping moved across update"
            )
            after = _read_header(pid, addr2)

            self.assertEqual(after["version"], 2)
            self.assertNotEqual(after["payload_ptr"], 0)
            self.assertGreater(before["timestamp_ns"], 0)
            self.assertGreaterEqual(
                after["timestamp_ns"], before["timestamp_ns"]
            )
            self.assertIn(b"otel-second", after["payload"])

    @unittest.skipUnless(
        sys.platform.startswith("linux"), "requires /proc/<pid>/{maps,mem}"
    )
    def test_unpublish_removes_mapping(self):
        """Unpublishing removes the mapping, a later publish recreates it."""
        with subprocess.Popen(
            _script_cmd("publisher.py"),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        ) as proc:
            pid = int(proc.stdout.readline())
            self.assertIsNotNone(_find_otel_ctx_addr(pid))

            proc.stdin.write("unpublish\n")
            proc.stdin.flush()
            self.assertEqual(proc.stdout.readline(), "done\n")
            self.assertIsNone(
                _find_otel_ctx_addr(pid),
                "OTEL_CTX mapping survived unpublish",
            )

            proc.stdin.write("update\n")
            proc.stdin.flush()
            self.assertEqual(proc.stdout.readline(), "done\n")
            self.assertIsNotNone(
                _find_otel_ctx_addr(pid),
                "OTEL_CTX mapping not recreated after re-publish",
            )
