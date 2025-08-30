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
    docker run -d --name books-db -p 3306:3306 books-db
    cd ..

Check that the run worked and the general log is available:

.. code-block:: sh

    docker exec -it books-db tail -f /var/log/general.log

Run OpenTelemetry Collector
---------------------------

Running the OpenTelemetry collector will show the MySQL instrumentor's
comment-in-span-attribute feature that the example has also been enabled.

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
        opentelemetry-instrumentation-mysql
    pip install mysql-connector-python

Then, run this script, which instruments all mysql-connector calls with
two sqlcommenter features opted in. For each ``SELECT`` call, a query is
made with a sqlcomment appended and one OTel span with ``db.statement``
attribute is also generated with sqlcomment.

.. code-block:: sh

    python instrumented_query.py


References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
* `OpenTelemetry Collector <https://github.com/open-telemetry/opentelemetry-collector>`_
* `OpenTelemetry MySQL instrumentation <https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/instrumentation/opentelemetry-instrumentation-mysql>`_