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

import pymemcache

from opentelemetry import trace as trace_api
from opentelemetry.ext.pymemcache import PymemcacheInstrumentor
from opentelemetry.test.test_base import TestBase
from opentelemetry.trace import get_tracer

from .utils import MockSocket, _str

TEST_HOST = "localhost"
TEST_PORT = 117711


class PymemcacheClientTestCase(TestBase):
    """ Tests for a patched pymemcache.client.base.Client. """

    def setUp(self):
        super().setUp()
        PymemcacheInstrumentor().instrument()

        # pylint: disable=protected-access
        self.tracer = get_tracer(__name__)

    def tearDown(self):
        super().tearDown()
        PymemcacheInstrumentor().uninstrument()

    def make_client(self, mock_socket_values, **kwargs):
        self.client = pymemcache.client.base.Client(
            (TEST_HOST, TEST_PORT), **kwargs
        )
        self.client.sock = MockSocket(list(mock_socket_values))
        return self.client

    def check_spans(self, spans, num_expected, queries_expected):
        """A helper for validating basic span information."""
        self.assertEqual(num_expected, len(spans))

        for span, query in zip(spans, queries_expected):
            self.assertEqual(span.name, "memcached.command")
            self.assertIs(span.kind, trace_api.SpanKind.INTERNAL)
            self.assertEqual(
                span.attributes["net.peer.name"], "{}".format(TEST_HOST)
            )
            self.assertEqual(span.attributes["net.peer.port"], TEST_PORT)
            self.assertEqual(span.attributes["db.type"], "memcached")
            self.assertEqual(
                span.attributes["db.url"],
                "memcached://{}:{}".format(TEST_HOST, TEST_PORT),
            )
            self.assertEqual(span.attributes["db.statement"], query)

    def test_set_success(self):
        client = self.make_client([b"STORED\r\n"])
        result = client.set(b"key", b"value", noreply=False)
        assert result is True

        spans = self.memory_exporter.get_finished_spans()

        self.check_spans(spans, 1, ["set key"])

    def test_get_many_none_found(self):
        client = self.make_client([b"END\r\n"])
        result = client.get_many([b"key1", b"key2"])
        assert result == {}

        spans = self.memory_exporter.get_finished_spans()

        self.check_spans(spans, 1, ["get_many key1 key2"])

    def test_get_multi_none_found(self):
        client = self.make_client([b"END\r\n"])
        # alias for get_many
        result = client.get_multi([b"key1", b"key2"])
        assert result == {}

        spans = self.memory_exporter.get_finished_spans()

        self.check_spans(spans, 1, ["get_multi key1 key2"])

    def test_set_multi_success(self):
        client = self.make_client([b"STORED\r\n"])
        # Alias for set_many, a convienance function that calls set for every key
        result = client.set_multi({b"key": b"value"}, noreply=False)
        assert result is True

        spans = self.memory_exporter.get_finished_spans()

        self.check_spans(spans, 2, ["set key", "set_multi key"])

    def test_delete_not_found(self):
        client = self.make_client([b"NOT_FOUND\r\n"])
        result = client.delete(b"key", noreply=False)
        assert result is False

        spans = self.memory_exporter.get_finished_spans()

        self.check_spans(spans, 1, ["delete key"])

    def test_incr_found(self):
        client = self.make_client([b"STORED\r\n", b"1\r\n"])
        client.set(b"key", 0, noreply=False)
        result = client.incr(b"key", 1, noreply=False)
        assert result == 1

        spans = self.memory_exporter.get_finished_spans()

        self.check_spans(spans, 2, ["set key", "incr key"])

    def test_get_found(self):
        client = self.make_client(
            [b"STORED\r\n", b"VALUE key 0 5\r\nvalue\r\nEND\r\n"]
        )
        result = client.set(b"key", b"value", noreply=False)
        result = client.get(b"key")
        assert result == b"value"

        spans = self.memory_exporter.get_finished_spans()

        self.check_spans(spans, 2, ["set key", "get key"])

    def test_decr_found(self):
        client = self.make_client([b"STORED\r\n", b"1\r\n"])
        client.set(b"key", 2, noreply=False)
        result = client.decr(b"key", 1, noreply=False)
        assert result == 1

        spans = self.memory_exporter.get_finished_spans()

        self.check_spans(spans, 2, ["set key", "decr key"])

    def test_add_stored(self):
        client = self.make_client([b"STORED\r", b"\n"])
        result = client.add(b"key", b"value", noreply=False)
        assert result is True

        spans = self.memory_exporter.get_finished_spans()

        self.check_spans(spans, 1, ["add key"])

    def test_delete_many_found(self):
        client = self.make_client([b"STORED\r", b"\n", b"DELETED\r\n"])
        result = client.add(b"key", b"value", noreply=False)
        # a convienance function that calls delete for every key
        result = client.delete_many([b"key"], noreply=False)
        assert result is True

        spans = self.memory_exporter.get_finished_spans()

        self.check_spans(
            spans, 3, ["add key", "delete key", "delete_many key"]
        )

    def test_set_many_success(self):
        client = self.make_client([b"STORED\r\n"])
        # a convienance function that calls set for every key
        result = client.set_many({b"key": b"value"}, noreply=False)
        assert result is True

        spans = self.memory_exporter.get_finished_spans()

        self.check_spans(spans, 2, ["set key", "set_many key"])

    def test_set_get(self):
        client = self.make_client(
            [b"STORED\r\n", b"VALUE key 0 5\r\nvalue\r\nEND\r\n"]
        )
        client.set(b"key", b"value", noreply=False)
        result = client.get(b"key")
        assert _str(result) == "value"

        spans = self.memory_exporter.get_finished_spans()

        self.assertEqual(len(spans), 2)
        self.assertEqual(
            spans[0].attributes["db.url"],
            "memcached://{}:{}".format(TEST_HOST, TEST_PORT),
        )
