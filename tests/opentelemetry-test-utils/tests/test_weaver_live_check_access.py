# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import json
import os
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

from opentelemetry.test.weaver_live_check import LiveCheckError, LiveCheckReport, WeaverLiveCheck


class TestReportAccess(unittest.TestCase):
    def test_report_can_be_serialized_without_losing_fields(self):
        raw = {"samples": [{"span": {"name": "test"}}], "statistics": {"count": 1}, "extra": [1]}
        report = LiveCheckReport(raw)
        self.assertEqual(json.loads(json.dumps(report.to_dict())), raw)
        self.assertEqual(report.samples, raw["samples"])
        self.assertEqual(report.statistics, raw["statistics"])
        report.to_dict()["extra"].append(2)
        report.samples[0]["span"]["name"] = "changed"
        report.statistics["count"] = 2
        self.assertEqual(report["extra"], [1])
        self.assertEqual(report.samples[0]["span"]["name"], "test")
        self.assertEqual(report.statistics["count"], 1)

    def test_missing_report_sections(self):
        report = LiveCheckReport({})
        self.assertEqual(report.samples, [])
        self.assertEqual(report.statistics, {})


class TestWeaverOptions(unittest.TestCase):
    @patch("opentelemetry.test.weaver_live_check.shutil.which", return_value="weaver")
    def test_named_options(self, _which):
        for data in ("data/*.json", "data with spaces", "https://example.com/data.tar.gz[policies]"):
            with self.subTest(advice_data=data):
                weaver = WeaverLiveCheck(
                    registry="registry",
                    otlp_port=4317,
                    admin_port=4320,
                    config="config with spaces.toml",
                    advice_data=data,
                    extra_args=["--quiet"],
                )
                command = weaver._command
                self.assertEqual(command[command.index("--config") + 1], os.path.abspath("config with spaces.toml"))
                self.assertEqual(command[command.index("--advice-data") + 1], data)
                self.assertEqual(command[-1], "--quiet")

    @patch("opentelemetry.test.weaver_live_check.shutil.which", return_value="weaver")
    def test_optional_flags_are_omitted(self, _which):
        weaver = WeaverLiveCheck(registry="registry", otlp_port=4317, admin_port=4320)
        self.assertNotIn("--config", weaver._command)
        self.assertNotIn("--advice-data", weaver._command)


class TestWeaverOutput(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch("opentelemetry.test.weaver_live_check.shutil.which", return_value="weaver"))
        directory = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        self.stdout_path = directory / "stdout.log"
        self.stderr_path = directory / "stderr.log"
        self.stdout_path.write_bytes(b"output\xff\n")
        self.stderr_path.write_text("diagnostic\n", encoding="utf-8")
        self.weaver = WeaverLiveCheck(registry="registry", otlp_port=4317, admin_port=4320)
        self.weaver._stdout_path = str(self.stdout_path)
        self.weaver._stderr_path = str(self.stderr_path)
        self.process = Mock()
        self.process.poll.return_value = None
        self.weaver._process = self.process
        self.addCleanup(self.weaver.close)

    def test_reading_output_does_not_stop_process(self):
        self.assertEqual(self.weaver.stdout, "output\ufffd\n")
        self.assertEqual(self.weaver.stderr, "diagnostic\n")
        self.process.assert_not_called()
        self.assertEqual(self.process.mock_calls, [])
        self.stderr_path.write_text("more diagnostics\n", encoding="utf-8")
        self.assertEqual(self.weaver.stderr, "more diagnostics\n")

    def test_close_retains_output_and_deletes_files(self):
        self.weaver.close()
        self.weaver.close()
        self.assertFalse(self.stdout_path.exists())
        self.assertFalse(self.stderr_path.exists())
        self.assertEqual(self.weaver.stdout, "output\ufffd\n")
        self.assertEqual(self.weaver.stderr, "diagnostic\n")

    def test_forced_exit_retains_output(self):
        self.process.wait.side_effect = [subprocess.TimeoutExpired("weaver", 5), 0]
        self.process.poll.side_effect = [None, 0]
        self.weaver.close()
        self.process.kill.assert_called_once_with()
        self.assertEqual(self.process.wait.call_count, 2)
        self.assertEqual(self.weaver.stderr, "diagnostic\n")

    def test_error_keeps_output_after_close(self):
        report = LiveCheckReport({})
        with patch.object(self.weaver, "_do_stop", return_value=(report, 1)):
            with self.assertRaises(LiveCheckError) as caught:
                self.weaver.end_and_check()
        self.weaver.close()
        self.assertEqual(caught.exception.stdout, "output\ufffd\n")
        self.assertEqual(caught.exception.stderr, "diagnostic\n")

    def test_missing_output_file_preserves_last_read(self):
        self.assertEqual(self.weaver.stderr, "diagnostic\n")
        self.stderr_path.unlink()
        self.assertEqual(self.weaver.stderr, "diagnostic\n")

    def test_error_constructor_remains_compatible(self):
        error = LiveCheckError("violation", LiveCheckReport({}))
        self.assertEqual(error.stdout, "")
        self.assertEqual(error.stderr, "")
