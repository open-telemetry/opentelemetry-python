sqlcommenter
============

This is an example of how to use OpenTelemetry Python instrumention with
sqlcommenter to enrich database query statements with contextual information.
For more information on sqlcommenter concepts, see:

* `Semantic Conventions - Database Spans <https://github.com/open-telemetry/semantic-conventions/blob/main/docs/database/database-spans.md#sql-commenter>`_
* `sqlcommenter <https://google.github.io/sqlcommenter/>`_

The source files of this example are available `here <https://github.com/open-telemetry/opentelemetry-python/tree/main/docs/examples/sqlcommenter/>`_.
This example uses Docker to manage a database server and OpenTelemetry collector.

Run MySQL server
----------------

A running MySQL server with general logs enabled will store query statements with context resulting from the sqlcommenter feature enabled in this example.

.. code-block:: sh

    cd books_database
    docker build -t books-db .
    docker run -d --name books-db -p 3366:3306 books-db
    cd ..

Check that the run is working and the general log is available:

.. code-block:: sh

    docker exec -it books-db tail -f /var/log/general.log

Run OpenTelemetry Collector
---------------------------

Running the OpenTelemetry collector will show the MySQL instrumentor's
comment-in-span-attribute feature, which this example has also enabled.

.. code-block:: sh

    docker run \
        -p 4317:4317 \
        -v $(pwd)/collector-config.yaml:/etc/otel/config.yaml \
        otel/opentelemetry-collector-contrib:latest

Run the sqlcommenter example
----------------------------

Set up and activate a Python virtual environment. Install these
dependencies of the sqlcommenter example:

.. code-block:: sh

    pip install opentelemetry-sdk \
        opentelemetry-exporter-otlp-proto-grpc \
        opentelemetry-instrumentation-mysql \
        mysql-connector-python

Then, run this script, which instruments all mysql-connector calls with
two sqlcommenter features opted in.

.. code-block:: sh

    python instrumented_query.py

Note that OpenTelemetry instrumentation with sqlcommenter is also
available for other Python database client drivers/object relation
mappers (ORMs). See full list at `instrumentation`_.

.. _instrumentation: https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/instrumentation

Check MySQL server general log and spans for sqlcomment
-------------------------------------------------------

After running the query script, check the MySQL general log contents:

.. code-block:: sh

    docker exec -it books-db tail -f /var/log/general.log

For each instrumented ``SELECT`` call, a query was made and logged with
a sqlcomment appended. For example:

.. code::

    2025-09-02T18:49:06.981980Z	  186 Query	SELECT * FROM authors WHERE id = 1 /*db_driver='mysql.connector%%3A9.4.0',dbapi_level='2.0',dbapi_threadsafety=1,driver_paramstyle='pyformat',mysql_client_version='9.4.0',traceparent='00-2c45248f2beefdd9688b0a94eb4ac9ee-4f3af9a825aae9b1-01'*/

In the running OpenTelemetry collector, you'll also see one span per
``SELECT`` call. Each of those span's trace ID and span ID will
correspond to a query log sqlcomment. With the comment-in-attribute
feature enabled, the span's ``db.statement`` attribute will also contain
the sqlcomment. For example:

.. code::

    ScopeSpans #0
    ScopeSpans SchemaURL: https://opentelemetry.io/schemas/1.11.0
    InstrumentationScope opentelemetry.instrumentation.mysql 0.57b0
    Span #0
        Trace ID       : 2c45248f2beefdd9688b0a94eb4ac9ee
        Parent ID      :
        ID             : 4f3af9a825aae9b1
        Name           : SELECT
        Kind           : Client
        Start time     : 2025-09-02 18:49:06.982341 +0000 UTC
        End time       : 2025-09-02 18:49:06.98463 +0000 UTC
        Status code    : Unset
        Status message :
    Attributes:
        -> db.system: Str(mysql)
        -> db.name: Str(books)
        -> db.statement: Str(SELECT * FROM authors WHERE id = %s /*db_driver='mysql.connector%%3A9.4.0',dbapi_level='2.0',dbapi_threadsafety=1,driver_paramstyle='pyformat',mysql_client_version='9.4.0',traceparent='00-2c45248f2beefdd9688b0a94eb4ac9ee-4f3af9a825aae9b1-01'*/)
        -> db.user: Str(books)
        -> net.peer.name: Str(localhost)
        -> net.peer.port: Int(3366)


References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
* `OpenTelemetry Collector <https://github.com/open-telemetry/opentelemetry-collector>`_
* `OpenTelemetry MySQL instrumentation <https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/instrumentation/opentelemetry-instrumentation-mysql>`_
* `Semantic Conventions - Database Spans <https://github.com/open-telemetry/semantic-conventions/blob/main/docs/database/database-spans.md#sql-commenter>`_
* `sqlcommenter <https://google.github.io/sqlcommenter/>`_