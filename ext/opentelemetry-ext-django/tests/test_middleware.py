from django.test import Client
from opentelemetry.test.wsgitestutil import WsgiTestBase


class TestDjangoOpenTracingMiddleware(WsgiTestBase):

    def test_middleware_traced(self):
        client = Client()
        response = client.get('/traced/')
        span_list = self.memory_exporter.get_finished_spans()
        span_list
        response
        from ipdb import set_trace
        set_trace()
        True
