Installation
------------
.. code-block:: sh

    pip install -rrequirements.txt

Run application
---------------
.. code-block:: sh

    gunicorn app -c gunicorn.config.py

Please make sure Jaeger is running locally and the default agent host and port are exposed.
