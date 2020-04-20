from django.test import Client
from opentelemetry.test.wsgitestutil import WsgiTestBase


class TestDjangoOpenTracingMiddleware(WsgiTestBase):

    def test_middleware_traced(self):
        Client().get("/traced/")
        assert len(self.memory_exporter.get_finished_spans()) == 1

    def test_middleware_error(self):
        with self.assertRaises(ValueError):
            Client().get("/error/")
        assert len(self.memory_exporter.get_finished_spans()) == 1
