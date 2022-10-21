from logging import getLogger
from opentelemetry import trace
from opentelemetry.instrumentation.grpc import GrpcInstrumentorServer
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.instrumentation.propagators import(
    get_global_response_propagator
)
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider.add_span_processor(
    SimpleSpanProcessor(ConsoleSpanExporter())
)

_logger = getLogger(__name__)
tracer = trace.get_tracer(__name__)

def _rewrapped_grpc(response_hook:None,grpc_user):
    def _wrapped_grpc(start_response):
        def _start_response(response_headers, *args, **kwargs):
            # Creating a span with kind SERVER
            set_span_name = ""
            with tracer.start_as_current_span(set_span_name, kind=trace.SpanKind.SERVER) as span:
                propagator = get_global_response_propagator()
                if propagator:
                    propagator.inject(
                        response_headers
                    )
                if span:
                    span.set_attributes(
                        {
                            "span":span, 
                            "response_headers":response_headers
                        }
                    )
                    if(
                        span.is_recording()
                        and span.kind == trace.SpanKind.SERVER
                    ):
                        span_attributes = span.__getattribute__("response_headers")
                        if len(span_attributes) > 0:
                            span.set_attribute(span_attributes)
                else:
                    _logger.warning(
                        "gRPC OpenTelemetry span"
                        "missing at _start_response(%s)",
                    )
                if response_hook is not None:
                    response_hook(span,response_headers)
            return start_response(response_headers, *args, **kwargs)

        # Auto instrumentating gRPC and attaching a response hook
        grpc_server_instrumentor = GrpcInstrumentorServer()
        grpc_server_instrumentor.instrument(response_hook=response_hook)
        result = grpc_user(_start_response)
        return result
    return _wrapped_grpc

def _wrapped_begore_request(request_hook=None):
    def _before_request():
        with tracer.start_as_current_span("span_name", kind=trace.SpanKind.SERVER) as span:
            if request_hook:
                request_hook(span)
        
        activation = trace.use_span(span, end_on_exit=True)
        activation.__enter__()
        
    # Auto instrumenting gRPC request and attaching a request hook
    grpc_server_instrumentor = GrpcInstrumentorServer()
    grpc_server_instrumentor.instrument(request_hook=request_hook)
    return _before_request