# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from functools import partial

from opentelemetry import trace as trace_api
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.trace import Resource


def new_tracer(span_limits=None, resource=None) -> trace_api.Tracer:
    provider_factory = trace_sdk.TracerProvider
    if resource is not None:
        provider_factory = partial(provider_factory, resource=resource)
    return provider_factory(span_limits=span_limits).get_tracer(__name__)


def get_span_with_dropped_attributes_events_links():
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
    with tracer.start_as_current_span(
        "span", links=links, attributes=attributes
    ) as span:
        for index in range(131):
            span.add_event(f"event{index}", attributes=attributes)
        return span
