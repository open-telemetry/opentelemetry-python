OpenTelemetry Exemplars Example
===============================

Exemplars are example measurements for aggregations. While they are simple conceptually, exemplars can estimate any statistic about the input distribution, can provide links to sample traces for high latency requests, and much more.
For more information about exemplars and how they work in OpenTelemetry, see the `spec <https://github.com/open-telemetry/oteps/pull/113>`_

Examples
--------

Installation

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install matplotlib # may have to install Qt as well
    pip install numpy

    pip install opentelemetry-exporter-cloud-monitoring # if you want to export exemplars to cloud monitoring

Statistical exemplars
^^^^^^^^^^^^^^^^^^^^^

The opentelemetry SDK provides a way to sample exemplars statistically:

    - Exemplars will be picked to represent the input distribution, without unquantifiable bias
    - A "sample_count" attribute will be set on each exemplar to quantify how many measurements each exemplar represents

See 'statistical_exemplars.ipynb' for the example (TODO: how do I link this?)

Trace exemplars
^^^^^^^^^^^^^^^^^^

Trace exemplars are exemplars that have not been sampled statistically,
but instead aim to provide value as individual exemplars.
They will have a trace id/span id attached for the active trace when the exemplar was recorded,
and they may focus on measurements with abnormally high/low values.

'trace_exemplars.py' shows how to generate exemplars for a histogram aggregation.
Currently only the Google Cloud Monitoring exporter supports uploading these exemplars.
