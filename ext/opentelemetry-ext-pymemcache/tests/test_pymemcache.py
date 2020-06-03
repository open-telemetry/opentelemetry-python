# 3p
import unittest


from opentelemetry.ext.pymemcache import PymemcacheInstrumentor
from opentelemetry.test.test_base import TestBase
from opentelemetry import trace as trace_api
from opentelemetry.trace import get_tracer
from .utils import MockSocket, _str
import pymemcache

TEST_HOST = 'localhost'
TEST_PORT = 117711


class PymemcacheClientTestCaseMixin(TestBase):
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
        self.client = pymemcache.client.base.Client((TEST_HOST, TEST_PORT), **kwargs)
        self.client.sock = MockSocket(list(mock_socket_values))
        return self.client        

    def test_set_get(self):
        client = self.make_client([b'STORED\r\n', b'VALUE key 0 5\r\nvalue\r\nEND\r\n'])
        client.set(b'key', b'value', noreply=False)
        result = client.get(b'key')
        assert _str(result) == 'value'

        spans = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(spans), 2)
        self.assertEqual(spans[0].attributes["db.url"], "memcached://{}:{}".format(TEST_HOST, TEST_PORT))
