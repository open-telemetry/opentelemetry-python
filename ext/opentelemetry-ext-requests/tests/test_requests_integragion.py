import unittest

import requests
from opentelemetry.ext.requests import enable as enable_requests_integration
from opentelemetry.trace import tracer

class TestRequestsIntegration(unittest.TestCase):

    def test_basic(self):
        enable_requests_integration(tracer())
        response = requests.get(url='https://www.example.org/')

