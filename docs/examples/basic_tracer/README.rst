Basic Tracer
============

This example shows how to use OpenTelemetry to instrument a Python application - e.g. a batch job.

The source files of this example are available :scm_web:`here <docs/examples/basic_tracer/>`.

Installation
------------

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk

Run the Example
---------------

.. code-block:: sh

    python tracer.py

The output will be displayed in the console:

::

    Hello world from OpenTelemetry Python!
    Span(name="baz", context=SpanContext(trace_id=0xf906f80f64d57c71ea8da4dfbbd2ddf2, span_id=0x5611c1407e06e4d7, trace_state={}), kind=SpanKind.INTERNAL, parent=Span(name="bar", context=SpanContext(trace_id=0xf906f80f64d57c71ea8da4dfbbd2ddf2, span_id=0x1b9db0e0cc1a3f60, trace_state={})), start_time=2019-11-07T21:26:45.934412Z, end_time=2019-11-07T21:26:45.934567Z)
    Span(name="bar", context=SpanContext(trace_id=0xf906f80f64d57c71ea8da4dfbbd2ddf2, span_id=0x1b9db0e0cc1a3f60, trace_state={}), kind=SpanKind.INTERNAL, parent=Span(name="foo", context=SpanContext(trace_id=0xf906f80f64d57c71ea8da4dfbbd2ddf2, span_id=0x1d5d87441ec2f410, trace_state={})), start_time=2019-11-07T21:26:45.934396Z, end_time=2019-11-07T21:26:45.934576Z)
    Span(name="foo", context=SpanContext(trace_id=0xf906f80f64d57c71ea8da4dfbbd2ddf2, span_id=0x1d5d87441ec2f410, trace_state={}), kind=SpanKind.INTERNAL, parent=None, start_time=2019-11-07T21:26:45.934369Z, end_time=2019-11-07T21:26:45.934580Z)


Useful links
------------

- OpenTelemetry_
- :doc:`../../api/trace`

.. _OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python/