Flask + Gunicorn Example
========================

The source files of this example are available :scm_web:`here <docs/examples/fork-process-model/flask-gunicorn/>`.

Installation
------------
.. code-block:: sh

    pip install -rrequirements.txt

Run application
---------------
.. code-block:: sh

    gunicorn app -c gunicorn.conf.py
