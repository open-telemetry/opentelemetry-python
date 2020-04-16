"""
To trace sqlalchemy queries, add instrumentation to the engine class
using the patch method that **must be called before** importing sqlalchemy::

    # patch before importing `create_engine`
    from opentelemetry.instrumentation.sqlalchemy.patch import patch
    patch(sqlalchemy=True)

    # use SQLAlchemy as usual
    from sqlalchemy import create_engine

    engine = create_engine('sqlite:///:memory:')
    engine.connect().execute("SELECT COUNT(*) FROM users")
"""
from opentelemetry.auto_instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.instrumentation.sqlalchemy.patch import patch, unpatch


class SQLAlchemyInstrumentor(BaseInstrumentor):
    """An instrumentor for Redis
    See `BaseInstrumentor`
    """

    def _instrument(self):
        patch()

    def _uninstrument(self):
        unpatch()
