from django.test import SimpleTestCase, Client


class TestDjangoOpenTracingMiddleware(SimpleTestCase):

    def test_middleware_traced(self):
        client = Client()
        response = client.get('/traced/')
        assert response['numspans'] == '1'
