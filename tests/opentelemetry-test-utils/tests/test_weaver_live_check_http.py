# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import subprocess
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, call, patch

from requests import ConnectionError, HTTPError, Timeout

from opentelemetry.test.weaver_live_check import LiveCheckError, WeaverLiveCheck


class TestWeaverLiveCheckHTTP(unittest.TestCase):
    def setUp(self):
        module = "opentelemetry.test.weaver_live_check"
        self.patch(f"{module}.shutil.which", return_value="weaver")
        self.post = self.patch(f"{module}.post")
        self.get = self.patch(f"{module}.get")
        self.process = Mock()
        self.process.wait.return_value = 0
        self.process.poll.return_value = 0
        self.weaver = WeaverLiveCheck(registry="registry", otlp_port=4317, admin_port=4320)
        self.weaver._ready = True
        self.weaver._process = self.process
        self.stop_response = Mock()
        self.shutdown_response = Mock()
        self.post.side_effect = [self.stop_response, self.shutdown_response]
        self.get.return_value.json.return_value = {"statistics": {"span_count": 1}}
        self.calls = Mock()
        self.calls.attach_mock(self.post, "post")
        self.calls.attach_mock(self.get, "get")
        self.calls.attach_mock(self.process.wait, "wait")
        self.addCleanup(self.weaver.close)

    def patch(self, target, **kwargs):
        patcher = patch(target, **kwargs)
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result

    def assert_lifecycle(self, timeout=30):
        self.assertEqual(
            [c for c in self.calls.mock_calls if c[0] in ("post", "get", "wait")],
            [
                call.post("http://localhost:4320/stop", timeout=timeout),
                call.get("http://localhost:4320/report", timeout=timeout),
                call.post("http://localhost:4320/shutdown", timeout=timeout),
                call.wait(timeout=timeout),
            ],
        )
        self.stop_response.raise_for_status.assert_called_once_with()
        self.stop_response.json.assert_not_called()
        self.get.return_value.raise_for_status.assert_called_once_with()
        self.shutdown_response.raise_for_status.assert_called_once_with()

    def test_end_reads_report_before_shutdown(self):
        self.process.wait.return_value = 1
        report = self.weaver.end(timeout=17)
        self.assertEqual(report["statistics"], {"span_count": 1})
        self.assertIs(self.weaver.end(), report)
        self.assert_lifecycle(timeout=17)
        self.weaver.close()
        self.weaver.close()
        self.assertIs(self.weaver.end(), report)
        with self.assertRaises(LiveCheckError) as caught:
            self.weaver.end_and_check()
        self.assertIs(caught.exception.report, report)
        self.assert_lifecycle(timeout=17)
        self.process.terminate.assert_not_called()

    def test_end_and_check_success(self):
        report = self.weaver.end_and_check()
        self.assertEqual(report["statistics"], {"span_count": 1})
        self.assertIs(self.weaver.end_and_check(), report)
        self.assertIs(self.weaver.end(), report)
        self.assert_lifecycle()

    def test_end_and_check_violations(self):
        self.process.wait.return_value = 1
        self.get.return_value.json.return_value = {
            "live_check_result": {"all_advice": [{"level": "violation", "id": "test", "message": "Invalid attribute"}]}
        }
        with self.assertRaisesRegex(LiveCheckError, "Invalid attribute") as caught:
            self.weaver.end_and_check()
        self.assertEqual(caught.exception.report.violations[0]["id"], "test")
        self.weaver.close()
        self.assertIs(self.weaver.end(), caught.exception.report)
        with self.assertRaises(LiveCheckError) as repeated:
            self.weaver.end_and_check()
        self.assertIs(repeated.exception.report, caught.exception.report)
        self.assert_lifecycle()

    def assert_no_completed_report(self):
        calls_before = list(self.calls.mock_calls)
        for end in (self.weaver.end, self.weaver.end_and_check):
            with self.subTest(method=end.__name__), self.assertRaisesRegex(RuntimeError, "without a completed report"):
                end()
        self.assertEqual(self.calls.mock_calls, calls_before)

    def test_close_shuts_down_without_raising_for_violations(self):
        self.process.wait.return_value = 1
        self.weaver.close()
        self.weaver.close()
        self.assert_no_completed_report()
        self.assert_lifecycle()

    def test_report_http_error_still_shuts_down(self):
        self.get.return_value.raise_for_status.side_effect = HTTPError("report unavailable")
        with self.assertLogs(level="ERROR"), self.assertRaisesRegex(HTTPError, "report unavailable"):
            self.weaver.end()
        self.post.assert_called_with("http://localhost:4320/shutdown", timeout=30)
        self.process.wait.assert_any_call(timeout=30)
        self.get.return_value.json.assert_not_called()
        self.assert_no_completed_report()

    def test_report_decode_error_still_shuts_down(self):
        self.get.return_value.json.side_effect = ValueError("invalid JSON")
        with self.assertLogs(level="ERROR"), self.assertRaisesRegex(ValueError, "invalid JSON"):
            self.weaver.end_and_check()
        self.assert_no_completed_report()
        self.post.assert_called_with("http://localhost:4320/shutdown", timeout=30)
        self.process.wait.assert_any_call(timeout=30)

    def test_report_error_preserved_when_shutdown_also_fails(self):
        self.get.side_effect = HTTPError("report unavailable")
        self.shutdown_response.raise_for_status.side_effect = HTTPError("shutdown failed")
        self.process.poll.return_value = None
        with self.assertLogs(level="ERROR"), self.assertRaisesRegex(HTTPError, "report unavailable"):
            self.weaver.end()
        self.process.kill.assert_called_once_with()
        self.process.wait.assert_called_once_with(timeout=5)

    def test_close_cleans_up_when_report_fails(self):
        self.get.side_effect = HTTPError("report unavailable")
        with self.assertLogs(level="ERROR"):
            self.weaver.close()
        self.post.assert_called_with("http://localhost:4320/shutdown", timeout=30)
        self.process.wait.assert_any_call(timeout=30)

    def test_shutdown_timeout_kills_process(self):
        self.process.wait.side_effect = [subprocess.TimeoutExpired("weaver", 30), 0]
        self.process.poll.side_effect = [None, 0]
        with self.assertLogs(level="ERROR"), self.assertRaises(subprocess.TimeoutExpired):
            self.weaver.end()
        self.process.kill.assert_called_once_with()
        self.assertEqual(self.process.wait.call_args_list, [call(timeout=30), call(timeout=5)])
        self.assert_no_completed_report()


class TestWeaverReadiness(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        module = "opentelemetry.test.weaver_live_check"
        stack.enter_context(patch(f"{module}.shutil.which", return_value="weaver"))
        self.get = stack.enter_context(patch(f"{module}.get"))
        self.clock = stack.enter_context(patch(f"{module}.time.monotonic", return_value=0))
        self.sleep = stack.enter_context(patch(f"{module}.time.sleep", side_effect=self.advance_clock))
        self.weaver = WeaverLiveCheck(registry="registry", otlp_port=4317, admin_port=4320, startup_timeout=0.5)
        self.process = Mock()
        self.process.poll.return_value = None
        self.weaver._process = self.process

    def advance_clock(self, seconds):
        self.clock.return_value += seconds

    def test_connection_refused_and_unhealthy_responses_are_quiet(self):
        self.weaver._startup_timeout = 30
        self.get.side_effect = [ConnectionError("refused"), Mock(status_code=503), Mock(status_code=200)]
        with self.assertNoLogs(level="WARNING"):
            self.weaver._wait_for_ready()
        self.assertEqual(self.get.call_count, 3)
        self.assertEqual(self.sleep.call_count, 2)

    def test_custom_timeout_allows_slow_startup(self):
        self.weaver = WeaverLiveCheck(registry="registry", otlp_port=4317, admin_port=4320, startup_timeout=60)
        self.weaver._process = self.process
        self.clock.side_effect = [0, 0, 40, 40]
        self.get.side_effect = [ConnectionError("refused"), Mock(status_code=200)]
        self.weaver._wait_for_ready()
        self.assertEqual(self.get.call_count, 2)

    def test_timeout_limits_requests_and_sleep(self):
        self.get.side_effect = Timeout("health timed out")
        with self.assertRaisesRegex(TimeoutError, "within 0.5 seconds") as caught:
            self.weaver._wait_for_ready()
        self.assertIsInstance(caught.exception.__cause__, Timeout)
        self.assertEqual(
            self.get.call_args_list,
            [
                call("http://localhost:4320/health", timeout=0.5, allow_redirects=False),
                call("http://localhost:4320/health", timeout=0.25, allow_redirects=False),
            ],
        )
        self.assertEqual(self.sleep.call_args_list, [call(0.25), call(0.25)])

    def test_redirect_is_not_ready(self):
        self.get.return_value.status_code = 302
        with self.assertRaises(TimeoutError):
            self.weaver._wait_for_ready()

    def test_process_exit_fails_without_waiting_for_deadline(self):
        self.process.poll.side_effect = [None, 1]
        self.process.returncode = 1
        self.get.side_effect = ConnectionError("refused")
        with self.assertRaisesRegex(RuntimeError, r"exited unexpectedly \(code 1\)"):
            self.weaver._wait_for_ready()
        self.get.assert_called_once()

    def test_startup_timeout_must_be_positive(self):
        for timeout in (0, -1):
            with self.subTest(timeout=timeout), self.assertRaisesRegex(ValueError, "must be positive"):
                WeaverLiveCheck(startup_timeout=timeout)
