# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Builders for spans that exporter tests need.

Both functions here build SDK objects directly instead of going through the API
globals, so they can be used from a test that is not based on
:class:`opentelemetry.test.test_base.TestBase`.
"""

from functools import partial

from opentelemetry import trace as trace_api
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.trace import Resource


def new_tracer(span_limits=None, resource=None) -> trace_api.Tracer:
    """Build a tracer from a brand new SDK tracer provider.

    The provider has no span processor, so a span this tracer starts is
    recorded in memory and exported nowhere. Use it when the test is about what
    a span contains rather than about what an exporter does with it.

    Args:
        span_limits: Limits on attribute, event and link counts and on
            attribute value length, applied to spans this tracer starts. When
            ``None``, the provider reads the limits from the environment, which
            means a test that sets one of the ``OTEL_SPAN_*`` variables
            influences the result.
        resource: Resource to attach to spans this tracer starts. When
            ``None``, the provider builds the default resource, which detects
            the service name and the SDK attributes from the environment.

    Returns:
        A tracer named after this module, ``opentelemetry.test.spantestutil``,
        from a provider that no other call shares.
    """
    provider_factory = trace_sdk.TracerProvider
    if resource is not None:
        provider_factory = partial(provider_factory, resource=resource)
    return provider_factory(span_limits=span_limits).get_tracer(__name__)


def get_span_with_dropped_attributes_events_links():
    """Build one ended span that has dropped attributes, events and links.

    Exporters have to report what the SDK discarded, and the counts are only
    non-zero once a limit is exceeded, so this builds a span that exceeds every
    one of them. The default ``SpanLimits`` cap attributes, events and links at
    128 each; this span is given 130 attributes, 131 events and 129 links, and
    its resource and every one of its events and links are given the same 130
    attributes. Only the resource keeps all 130, because no limit applies to it;
    the span, each event and each link keep the 128 the limits allow. The span
    name is ``"span"``.

    Returns:
        The span, already ended, because it is returned from inside the
        ``start_as_current_span`` block and the context manager ends it on the
        way out. Reading ``dropped_attributes``, ``dropped_events`` and
        ``dropped_links`` on it gives non-zero counts.
    """
    attributes = {}
    for index in range(130):
        attributes[f"key{index}"] = [f"value{index}"]
    links = []
    for index in range(129):
        links.append(
            trace_api.Link(
                trace_sdk._Span(
                    name=f"span{index}",
                    context=trace_api.INVALID_SPAN_CONTEXT,
                    attributes=attributes,
                ).get_span_context(),
                attributes=attributes,
            )
        )

    tracer = new_tracer(
        span_limits=trace_sdk.SpanLimits(),
        resource=Resource(attributes=attributes),
    )
    with tracer.start_as_current_span("span", links=links, attributes=attributes) as span:
        for index in range(131):
            span.add_event(f"event{index}", attributes=attributes)
        return span
