import unittest

import opentelemetry_example_app.flask_example as flask_example


class TestFlaskExample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = flask_example.app

    def test_full_path(self):
        with self.app.test_client() as client:
            response = client.get("/")
            assert response.data.decode() == "hello"
