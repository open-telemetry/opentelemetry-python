# stdlib
import contextlib

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 3rd party
from opentelemetry import trace
from opentelemetry.instrumentation.sqlalchemy.engine import trace_engine

from .utils import TracerTestBase

Base = declarative_base()


def _create_engine(engine_args):
    # create a SQLAlchemy engine
    config = dict(engine_args)
    url = config.pop("url")
    return create_engine(url, **config)


class Player(Base):
    """Player entity used to test SQLAlchemy ORM"""

    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    name = Column(String(20))


class SQLAlchemyTestMixin(TracerTestBase):

    """SQLAlchemy test mixin that includes a complete set of tests
    that must be executed for different engine. When a new test (or
    a regression test) should be added to SQLAlchemy test suite, a new
    entry must be appended here so that it will be executed for all
    available and supported engines. If the test is specific to only
    one engine, that test must be added to the specific `TestCase`
    implementation.

    To support a new engine, create a new `TestCase` that inherits from
    `SQLAlchemyTestMixin` and `TestCase`. Then you must define the following
    static class variables:
    * VENDOR: the database vendor name
    * SQL_DB: the `sql.db` tag that we expect (it's the name of the database available in the `.env` file)
    * SERVICE: the service that we expect by default
    * ENGINE_ARGS: all arguments required to create the engine

    To check specific tags in each test, you must implement the
    `check_meta(self, span)` method.
    """

    VENDOR = None
    SQL_DB = None
    SERVICE = None
    ENGINE_ARGS = None

    @contextlib.contextmanager
    def connection(self):
        # context manager that provides a connection
        # to the underlying database
        try:
            conn = self.engine.connect()
            yield conn
        finally:
            conn.close()

    def check_meta(self, span):
        """function that can be implemented according to the
        specific engine implementation
        """

    def setUp(self):
        # create an engine with the given arguments
        self.engine = _create_engine(self.ENGINE_ARGS)

        # create the database / entities and prepare a session for the test
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(self.engine, checkfirst=False)
        self.session = sessionmaker(bind=self.engine)()
        # trace the engine
        trace_engine(self.engine, self._tracer)
        self._span_exporter.clear()

    def tearDown(self):
        # pylint: disable=invalid-name
        # clear the database and dispose the engine
        self.session.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        super(SQLAlchemyTestMixin, self).tearDown()

    def test_orm_insert(self):
        # ensures that the ORM session is traced
        wayne = Player(id=1, name="wayne")
        self.session.add(wayne)
        self.session.commit()

        traces = self.pop_traces()
        # trace composition
        assert len(traces) == 1
        span = traces[0]
        # span fields
        assert span.name == "{}.query".format(self.VENDOR)
        assert span.attributes.get("service") == self.SERVICE
        assert "INSERT INTO players" in span.attributes.get("resource")
        print(span.attributes)
        assert span.attributes.get("sql.db") == self.SQL_DB
        # assert span.get_metric("sql.rows") == 1
        self.check_meta(span)
        assert (
            span.status.canonical_code == trace.status.StatusCanonicalCode.OK
        )
        assert (span.end_time - span.start_time) > 0

    def test_session_query(self):
        # ensures that the Session queries are traced
        out = list(self.session.query(Player).filter_by(name="wayne"))
        assert len(out) == 0

        traces = self.pop_traces()
        # trace composition
        assert len(traces) == 1
        span = traces[0]
        # span fields
        assert span.name == "{}.query".format(self.VENDOR)
        assert span.attributes.get("service") == self.SERVICE
        assert (
            "SELECT players.id AS players_id, players.name AS players_name \nFROM players \nWHERE players.name"
            in span.attributes.get("resource")
        )
        assert span.attributes.get("sql.db") == self.SQL_DB
        self.check_meta(span)
        assert (
            span.status.canonical_code == trace.status.StatusCanonicalCode.OK
        )
        assert (span.end_time - span.start_time) > 0

    def test_engine_connect_execute(self):
        # ensures that engine.connect() is properly traced
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM players").fetchall()
            assert len(rows) == 0

        traces = self.pop_traces()
        # trace composition
        assert len(traces) == 1
        span = traces[0]
        # span fields
        assert span.name == "{}.query".format(self.VENDOR)
        assert span.attributes.get("service") == self.SERVICE
        assert span.attributes.get("resource") == "SELECT * FROM players"
        assert span.attributes.get("sql.db") == self.SQL_DB
        self.check_meta(span)
        assert (
            span.status.canonical_code == trace.status.StatusCanonicalCode.OK
        )
        assert (span.end_time - span.start_time) > 0

    def test_opentelemetry(self):
        """Ensure that sqlalchemy works with opentelemetry."""
        ot_tracer = trace.get_tracer("sqlalch_svc")

        with ot_tracer.start_as_current_span("sqlalch_op"):
            with self.connection() as conn:
                rows = conn.execute("SELECT * FROM players").fetchall()
                assert len(rows) == 0

        traces = self.pop_traces()
        # trace composition
        assert len(traces) == 2
        child_span, parent_span = traces

        # confirm the parenting
        assert parent_span.parent is None
        assert (
            child_span.parent.context.trace_id == parent_span.context.trace_id
        )

        assert parent_span.name == "sqlalch_op"
        assert parent_span.instrumentation_info.name == "sqlalch_svc"

        # span fields
        assert child_span.name == "{}.query".format(self.VENDOR)
        assert child_span.attributes.get("service") == self.SERVICE
        assert child_span.attributes.get("resource") == "SELECT * FROM players"
        assert child_span.attributes.get("sql.db") == self.SQL_DB
        assert (
            child_span.status.canonical_code
            == trace.status.StatusCanonicalCode.OK
        )
        assert (child_span.end_time - child_span.start_time) > 0

    def test_analytics_default(self):
        # ensures that the ORM session is traced
        wayne = Player(id=1, name="wayne")
        self.session.add(wayne)
        self.session.commit()

        spans = self._span_exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)
