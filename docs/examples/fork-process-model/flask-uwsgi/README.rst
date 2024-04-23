Installation
------------
.. code-block:: sh

    pip install -rrequirements

Run application
---------------

.. code-block:: sh

    uwsgi --http :8000 --wsgi-file app.py --callable application --master --enable-threads
