from unittest import mock

from opentelemetry.ext.asyncpg import AsyncPGInstrumentor
from opentelemetry.test.test_base import TestBase

import asyncpg


class TestAsyncPGWrapper(TestBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        AsyncPGInstrumentor().instrument(tracer_provider=cls.tracer_provider)

    @classmethod
    def tearDownClass(cls):
        super().tearDown()
        AsyncPGInstrumentor().uninstrument()

    def _execute(self):
        pass

    @mock.patch("asyncpg.connect")
    async def test_fetch(self):
        conn = await asyncpg.connect(user='user',
                                     password='password',
                                     database='database',
                                     host='127.0.0.1')


