import os
import unittest

import psycopg2
import pytest
from sqlalchemy.exc import ProgrammingError

from opentelemetry import trace

from .mixins import SQLAlchemyTestMixin

POSTGRES_CONFIG = {
    "host": "127.0.0.1",
    "port": int(os.getenv("TEST_POSTGRES_PORT", "5432")),
    "user": os.getenv("TEST_POSTGRES_USER", "testuser"),
    "password": os.getenv("TEST_POSTGRES_PASSWORD", "testpassword"),
    "dbname": os.getenv("TEST_POSTGRES_DB", "opentelemetry-tests"),
}


class PostgresTestCase(SQLAlchemyTestMixin, unittest.TestCase):
    """TestCase for Postgres Engine"""

    VENDOR = "postgres"
    SQL_DB = "opentelemetry-tests"
    SERVICE = "postgres"
    ENGINE_ARGS = {
        "url": "postgresql://%(user)s:%(password)s@%(host)s:%(port)s/%(dbname)s"
        % POSTGRES_CONFIG
    }

    def check_meta(self, span):
        # check database connection tags
        self.assertEqual(
            span.attributes.get("out.host"), POSTGRES_CONFIG["host"]
        )
        # self.assertEqual(span.get_metric("out.port"), POSTGRES_CONFIG["port"])

    def test_engine_execute_errors(self):
        # ensures that SQL errors are reported
        with pytest.raises(ProgrammingError):
            with self.connection() as conn:
                conn.execute("SELECT * FROM a_wrong_table").fetchall()

        traces = self.pop_traces()
        # trace composition
        self.assertEqual(len(traces), 1)
        span = traces[0]
        # span fields
        self.assertEqual(span.name, "{}.query".format(self.VENDOR))
        self.assertEqual(span.attributes.get("service"), self.SERVICE)
        self.assertEqual(
            span.attributes.get("resource"), "SELECT * FROM a_wrong_table"
        )
        self.assertEqual(span.attributes.get("sql.db"), self.SQL_DB)
        # self.assertIsNone(span.attributes.get("sql.rows") or span.get_metric("sql.rows"))
        self.check_meta(span)
        self.assertTrue(span.end_time - span.start_time > 0)
        # check the error
        self.assertEqual(
            span.status.canonical_code,
            trace.status.StatusCanonicalCode.UNKNOWN,
        )
        # TODO: error handling
        # self.assertTrue('relation "a_wrong_table" does not exist' in span.attributes.get("error.msg"))
        # assert "psycopg2.errors.UndefinedTable" in span.attributes.get("error.type")
        # assert 'UndefinedTable: relation "a_wrong_table" does not exist' in span.attributes.get("error.stack")


class PostgresCreatorTestCase(PostgresTestCase):
    """TestCase for Postgres Engine that includes the same tests set
    of `PostgresTestCase`, but it uses a specific `creator` function.
    """

    VENDOR = "postgres"
    SQL_DB = "opentelemetry-tests"
    SERVICE = "postgres"
    ENGINE_ARGS = {
        "url": "postgresql://",
        "creator": lambda: psycopg2.connect(**POSTGRES_CONFIG),
    }
