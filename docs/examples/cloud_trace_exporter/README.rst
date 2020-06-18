Cloud Trace Exporter Example
============================

These examples show how to use OpenTelemetry to send tracing data to Cloud Trace.


Basic Example
-------------

To use this exporter you first need to:
    * A Google Cloud project. You can `create one here <https://console.cloud.google.com/projectcreate>`_.
    * Enable Cloud Trace API (listed in the Cloud Console as Stackdriver Trace API) in the project `here <https://console.cloud.google.com/apis/library?q=cloud%20trace&filter=visibility:public>`_.
      * If the page says "API Enabled" then you're done! No need to do anything.
    * Enable Default Application Credentials by creating setting `GOOGLE_APPLICATION_CREDENTIALS <https://cloud.google.com/docs/authentication/getting-started>`_ or by `installing gcloud sdk <https://cloud.google.com/sdk/install>`_ and calling ``gcloud auth application-default login``.

* Installation

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install opentelemetry-exporter-cloud-trace

* Run an example locally

.. literalinclude:: basic_trace.py
    :language: python
    :lines: 1-

Checking Output
--------------------------

After running any of these examples, you can go to `Cloud Trace overview <https://console.cloud.google.com/traces/list>`_ to see the results.


Further Reading
--------------------------

* `More information about exporters in general <https://opentelemetry-python.readthedocs.io/en/stable/getting-started.html#configure-exporters-to-emit-spans-elsewhere>`_

Troubleshooting
--------------------------

Running basic_trace.py hangs:
#############################
    * Make sure you've setup Application Default Credentials. Either run ``gcloud auth application-default login`` or set the ``GOOGLE_APPLICATION_CREDENTIALS`` environment variable to be a path to a service account token file.

Getting error ``google.api_core.exceptions.ResourceExhausted: 429 Resource has been exhausted``:
################################################################################################
    * Check that you've enabled the `Cloud Trace (Stackdriver Trace) API <https://console.cloud.google.com/apis/library?q=cloud%20trace&filter=visibility:public>`_

bash: pip: command not found:
#############################
    * `Install pip <https://cloud.google.com/python/setup#installing_python>`_
    * If your machine uses python2 by default, pip will also be the python2 version. Try using ``pip3`` instead of ``pip``.

pip install is hanging
######################
Try upgrading pip

.. code-block:: sh

    pip install --upgrade pip

``pip install grcpio`` has been known to hang when you aren't using an upgraded version.

ImportError: No module named opentelemetry
##########################################
Make sure you are using python3. If

.. code-block:: sh

    python --version

returns ``Python 2.X.X`` try calling

.. code-block:: sh

    python3 basic_trace.py
