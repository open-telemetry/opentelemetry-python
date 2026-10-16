# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import os
import unittest
from unittest.mock import patch

# pylint: disable-next=import-error
from opentelemetry.exporter.http.transport._proxy import (
    _get_environ_proxy,
    _get_proxy_auth,
    _should_bypass_proxies,
)


class TestGetEnvironProxy(unittest.TestCase):
    def test_selects_proxy_for_url(self):
        cases = [
            ({"HTTP_PROXY": "http://proxy:3128"}, "http://example.test", "http://proxy:3128"),
            ({"HTTP_PROXY": "http://proxy:3128"}, "https://example.test", None),
            ({"HTTPS_PROXY": "http://proxy:3128"}, "https://example.test", "http://proxy:3128"),
            ({"HTTPS_PROXY": "http://proxy:3128"}, "http://example.test", None),
            ({"ALL_PROXY": "socks5h://proxy:1080"}, "https://example.test", "socks5h://proxy:1080"),
            (
                {"HTTPS_PROXY": "http://https-proxy:3128", "ALL_PROXY": "socks5://all-proxy:1080"},
                "https://example.test",
                "http://https-proxy:3128",
            ),
            (
                {"HTTPS_PROXY": "http://upper:3128", "https_proxy": "http://lower:3128"},
                "https://example.test",
                "http://lower:3128",
            ),
            ({"HTTP_PROXY": "proxy:3128"}, "http://example.test", "http://proxy:3128"),
            ({"all_proxy": "socks4a://proxy:1080"}, "http://example.test", "socks4a://proxy:1080"),
        ]
        for env, url, expected in cases:
            with self.subTest(env=env, url=url):
                with patch.dict(os.environ, env, clear=True):
                    self.assertEqual(_get_environ_proxy(url), expected)

    @patch.dict(os.environ, {"HTTPS_PROXY": "http://proxy:3128", "NO_PROXY": "example.test"}, clear=True)
    def test_returns_none_when_bypassed(self):
        self.assertIsNone(_get_environ_proxy("https://example.test/v1/traces"))

    @patch.dict(os.environ, {}, clear=True)
    @patch("opentelemetry.exporter.http.transport._proxy.getproxies", return_value={})
    def test_returns_none_without_proxies(self, _):
        self.assertIsNone(_get_environ_proxy("https://example.test/v1/traces"))


class TestShouldBypassProxies(unittest.TestCase):
    def test_no_proxy_matching(self):
        cases = [
            ("example.test", "http://example.test", True),
            ("example.test", "http://api.example.test", True),
            (".example.test", "http://api.example.test", True),
            ("example.test", "http://other.test", False),
            ("example.test:4318", "http://example.test:4318", True),
            ("example.test:4318", "http://example.test:4317", False),
            ("other.test, example.test", "http://example.test", True),
            ("*", "http://example.test", True),
            ("10.0.0.5", "http://10.0.0.5:4318", True),
            ("10.0.0.5", "http://10.0.0.6:4318", False),
            ("10.0.0.0/24", "http://10.0.0.6:4318", True),
            ("10.0.0.0/24", "http://10.0.1.6:4318", False),
        ]
        for no_proxy, url, expected in cases:
            with self.subTest(no_proxy=no_proxy, url=url):
                with patch.dict(
                    os.environ,
                    {"HTTP_PROXY": "http://proxy:3128", "NO_PROXY": no_proxy},
                    clear=True,
                ):
                    self.assertEqual(_should_bypass_proxies(url), expected)

    @patch.dict(
        os.environ,
        {"HTTP_PROXY": "http://proxy:3128", "NO_PROXY": "upper.test", "no_proxy": "lower.test"},
        clear=True,
    )
    def test_lowercase_no_proxy_takes_precedence(self):
        self.assertTrue(_should_bypass_proxies("http://lower.test"))
        self.assertFalse(_should_bypass_proxies("http://upper.test"))

    def test_url_without_hostname_is_bypassed(self):
        self.assertTrue(_should_bypass_proxies("file:///tmp/x"))


class TestGetProxyAuth(unittest.TestCase):
    def test_get_proxy_auth(self):
        cases = [
            ("http://proxy:3128", (None, None)),
            ("http://user:pass@proxy:3128", ("user", "pass")),
            ("socks5h://us%40er:p%3Ass@proxy:1080", ("us@er", "p:ss")),
            ("http://user@proxy:3128", ("user", "")),
        ]
        for proxy_url, expected in cases:
            with self.subTest(proxy_url=proxy_url):
                self.assertEqual(_get_proxy_auth(proxy_url), expected)
