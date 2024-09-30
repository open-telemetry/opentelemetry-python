from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import (
    Resource,
)
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

"""
This example shows how entities are used to create a Resource. There are 2
EntityDetector objects that are found via entry points. These EntityDetectors
create entities whose ids are {"a": "b"} and whose attributes are {"c": "d"}.
These entities are automatically detected and used when a Resource is created,
and their ids and attributes are put together as Resource attributes where they
show up as "a": "b" and "c": "d".

This example creates 3 spans that are created using a tracer that comes from a
TracerProvider that was created using a Resource which automatically uses the
entities mentioned above.

These 3 spans are exported to the console, the entities attributes can be found
in the "resource" section of the exported spans.
"""

tracer_provider = TracerProvider(
    resource=Resource.create_using_entities()
)

tracer = tracer_provider.get_tracer(__name__)

tracer_provider.add_span_processor(
    SimpleSpanProcessor(ConsoleSpanExporter())
)

with tracer.start_as_current_span("a"):
    with tracer.start_as_current_span("b"):
        with tracer.start_as_current_span("c"):
            pass
