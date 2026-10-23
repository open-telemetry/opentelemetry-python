# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import concurrent.futures
import io
import json
import os
import sys
import tempfile
import threading
import time
import unittest

from opentelemetry.exporter.otlp.json.file._internal import (
    _FileExporter,
    _format_line,
)

_LOGGER_NAME = "opentelemetry.exporter.otlp.json.file._internal"


class _ConcurrentVerificationStream:
    """A test stream that simulates non-atomic chunked writes and verifies mutual exclusion."""

    def __init__(self):
        self._chunks: list[str] = []
        self._active_writers = 0
        self.concurrent_write_detected = False
        self.closed = False
        self._tracking_lock = threading.Lock()

    def write(self, text: str) -> int:
        with self._tracking_lock:
            self._active_writers += 1
            if self._active_writers > 1:
                self.concurrent_write_detected = True
        try:
            # Emit in two chunks and cooperatively yield to expose missing synchronization
            mid = len(text) // 2
            self._chunks.append(text[:mid])
            time.sleep(0)
            self._chunks.append(text[mid:])
            return len(text)
        finally:
            with self._tracking_lock:
                self._active_writers -= 1

    def flush(self) -> None:
        pass

    def getvalue(self) -> str:
        return "".join(self._chunks)


class TestFormatLine(unittest.TestCase):
    def test_produces_valid_json(self):
        result = _format_line({"a": 1, "b": "hello"})
        parsed = json.loads(result.strip())
        self.assertEqual(parsed, {"a": 1, "b": "hello"})

    def test_newline_terminated(self):
        result = _format_line({"x": 0})
        self.assertTrue(result.endswith("\n"))

    def test_compact_no_spaces(self):
        result = _format_line({"a": 1, "b": 2})
        self.assertNotIn(" ", result)

    def test_nested_structure(self):
        entry = {"outer": {"inner": [1, 2, 3]}, "flag": True}
        result = _format_line(entry)
        parsed = json.loads(result.strip())
        self.assertEqual(parsed, entry)


class TestFileExporter(unittest.TestCase):
    def test_caller_stream_remains_open_after_shutdown(self):
        stream = io.StringIO()
        exporter = _FileExporter(
            encode=lambda data: data,
            kind="spans",
            stream=stream,
        )
        self.assertTrue(exporter.export({"sample": "record"}))
        exporter.shutdown()

        self.assertFalse(stream.closed)
        stream.write("subsequent write\n")
        self.assertEqual(
            stream.getvalue(),
            '{"sample":"record"}\nsubsequent write\n',
        )

    def test_default_stdout_remains_open_after_shutdown(self):
        exporter = _FileExporter(
            encode=lambda data: data,
            kind="spans",
        )
        self.assertIs(exporter._stream, sys.stdout)
        exporter.shutdown()
        self.assertFalse(sys.stdout.closed)

    def test_exporter_owned_file_stream_closes_after_shutdown(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "output.jsonl")
            exporter = _FileExporter(
                encode=lambda data: data,
                kind="spans",
                path=path,
            )
            file_stream = exporter._stream
            self.assertFalse(file_stream.closed)

            self.assertTrue(exporter.export({"event": "saved"}))
            exporter.shutdown()

            self.assertTrue(file_stream.closed)
            with open(path, encoding="utf-8") as file_handle:
                content = file_handle.read()
            self.assertEqual(content, '{"event":"saved"}\n')

    def test_export_to_closed_stream_returns_failure_and_logs_warning(self):
        stream = io.StringIO()
        exporter = _FileExporter(
            encode=lambda data: data,
            kind="spans",
            stream=stream,
        )
        stream.close()

        with self.assertLogs(_LOGGER_NAME, level="WARNING") as cm:
            result = exporter.export({"should": "fail"})

        self.assertFalse(result)
        self.assertTrue(
            any("Stream is closed, ignoring spans export call" in msg for msg in cm.output),
            f"Expected closed stream warning not found in logs: {cm.output}",
        )

    def test_concurrent_exports_produce_atomic_lines(self):
        stream = _ConcurrentVerificationStream()
        exporter = _FileExporter(
            encode=lambda data: data,
            kind="spans",
            stream=stream,
        )

        num_workers = 6
        items_per_worker = 20
        barrier = threading.Barrier(num_workers)

        def worker_task(worker_id: int):
            barrier.wait()
            for item_index in range(items_per_worker):
                success = exporter.export(
                    {
                        "worker_id": worker_id,
                        "item_index": item_index,
                        "payload": f"worker-{worker_id}-item-{item_index}",
                    }
                )
                if not success:
                    raise RuntimeError(f"Export failed for worker {worker_id}, item {item_index}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker_task, worker_id) for worker_id in range(num_workers)]
            for future in concurrent.futures.as_completed(futures):
                future.result()

        self.assertFalse(
            stream.concurrent_write_detected,
            "Concurrent writes were detected on the underlying stream",
        )
        lines = stream.getvalue().splitlines()
        self.assertEqual(len(lines), num_workers * items_per_worker)

        parsed_records = [json.loads(line) for line in lines]
        emitted_keys = {(record["worker_id"], record["item_index"]) for record in parsed_records}
        expected_keys = {
            (worker_id, item_index) for worker_id in range(num_workers) for item_index in range(items_per_worker)
        }
        self.assertEqual(emitted_keys, expected_keys)
