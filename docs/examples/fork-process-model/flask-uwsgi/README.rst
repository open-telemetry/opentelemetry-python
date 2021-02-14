Installation
------------
.. code-block:: sh

    pip install -rrequirements.txt

Run application
---------------

.. code-block:: sh

    uwsgi --http :8000 --wsgi-file app.py --callable application --master --enable-threads

Please make sure Jaeger is running locally and the default agent host and port are exposed.
