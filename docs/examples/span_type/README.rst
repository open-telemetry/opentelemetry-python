Span type
=========

Prototype for the `Span type OTEP
<https://github.com/open-telemetry/opentelemetry-specification/pull/4849>`_:
a span property that identifies the semantic convention definition the span
follows.

* API: ``span_type`` keyword argument on ``Tracer.start_span`` and
  ``Tracer.start_as_current_span``. Immutable, no setter.
* SDK: ``ReadableSpan.span_type``, plus ``span_type`` passed to
  ``Sampler.should_sample``.
* OTLP: emitted as the ``otel.span.type`` attribute until the protocol gains a
  top-level ``Span.type`` field.

Run
---

.. code-block:: sh

    pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc
    python span_type.py

A collector on ``localhost:4317`` is optional -- the example prints the encoded
OTLP payload either way.

Live check
----------

``test_span_type.py`` checks the example's span against
``weaver registry live-check`` using the schema v2 registry in ``registry/``,
which defines the ``gen_ai.client.inference`` span with one required and one
recommended attribute. ``weaver.toml`` filters out findings for the default SDK
resource attributes, which the registry deliberately does not define.

.. code-block:: sh

    pip install opentelemetry-test-utils pytest   # weaver binary also required
    pytest test_span_type.py

Live-check resolves the span by its type -- not by its name -- and then checks
it against that definition: the missing recommended ``gen_ai.request.model`` is
an improvement, a missing required attribute or an attribute the registry does
not define fails the check.

Requires a weaver build with span type support, and ``--v2`` -- without it
weaver downconverts the registry to v1, where spans have no type.
