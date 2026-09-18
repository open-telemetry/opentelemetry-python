Flask + uWSGI Example
=====================

The source files of this example are available :scm_web:`here <docs/examples/fork-process-model/flask-uwsgi/>`.

Installation
------------
.. code-block:: sh

    pip install -rrequirements.txt

Run application
---------------

.. code-block:: sh

    uwsgi --http :8000 --wsgi-file app.py --callable application --master --enable-threads
