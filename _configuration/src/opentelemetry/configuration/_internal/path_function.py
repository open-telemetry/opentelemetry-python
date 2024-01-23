# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest.mock import Mock
from urllib.parse import urlparse

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as GRPCOTLPSpanExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as HTTPOTLPSpanExporter,
)
from opentelemetry.exporter.zipkin.proto.http import ZipkinExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import (
    SpanLimits,
    SynchronousMultiSpanProcessor,
    TracerProvider,
)
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.sdk.trace.sampling import (
    ALWAYS_OFF,
    ALWAYS_ON,
    ParentBasedTraceIdRatio,
)

_resource = None


class MockSampler(Mock):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._args = args
        self._kwargs = kwargs

    def __repr__(self) -> str:
        args = list(self._args).copy()
        kwargs = self._kwargs.copy()

        kwargs.pop("type")
        args.extend([f"{key}={value}" for key, value in kwargs.items()])

        return f'{self.type}({", ".join(args)})'


def set_resource(resource):
    global _resource
    _resource = resource


def attribute_limits(
    attribute_count_limit: int = None,
    attribute_value_length_limit: int = None,
    **kwargs
):
    pass


def logger_provider(limits: object = None, processors: list = None):
    pass


def logger_provider_processors(
    batch: object = None, simple: object = None, **kwargs
):
    pass


def logger_provider_processors_batch(
    exporter: object,
    export_timeout: int = None,
    max_export_batch_size: int = None,
    max_queue_size: int = None,
    schedule_delay: int = None,
):
    pass


def logger_provider_processors_batch_exporter(otlp: object = None, **kwargs):
    pass


def logger_provider_processors_batch_exporter_otlp(
    endpoint: str,
    protocol: str,
    certificate: str = None,
    client_certificate: str = None,
    client_key: str = None,
    compression: str = None,
    headers: object = None,
    timeout: int = None,
):
    pass


def logger_provider_processors_batch_exporter_otlp_headers(**kwargs):
    pass


def logger_provider_processors_simple(exporter: object):
    pass


def logger_provider_processors_simple_exporter(otlp: object = None, **kwargs):
    pass


def logger_provider_processors_simple_exporter_otlp(
    endpoint: str,
    protocol: str,
    certificate: str = None,
    client_certificate: str = None,
    client_key: str = None,
    compression: str = None,
    headers: object = None,
    timeout: int = None,
):
    pass


def logger_provider_processors_simple_exporter_otlp_headers(**kwargs):
    pass


def logger_provider_limits(
    attribute_count_limit: int = None, attribute_value_length_limit: int = None
):
    pass


def meter_provider(readers: list = None, views: list = None):
    pass


def meter_provider_readers(periodic: object = None, pull: object = None):
    pass


def meter_provider_readers_periodic(
    exporter: object, interval: int = None, timeout: int = None
):
    pass


def meter_provider_readers_periodic_exporter(
    console: object = None,
    otlp: object = None,
    prometheus: object = None,
    **kwargs
):
    pass


def meter_provider_readers_periodic_exporter_otlp(
    endpoint: str,
    protocol: str,
    certificate: str = None,
    client_certificate: str = None,
    client_key: str = None,
    compression: str = None,
    default_histogram_aggregation: str = None,
    headers: object = None,
    temporality_preference: str = None,
    timeout: int = None,
):
    pass


def meter_provider_readers_periodic_exporter_otlp_headers(**kwargs):
    pass


def meter_provider_readers_periodic_exporter_console():
    pass


def meter_provider_readers_periodic_exporter_prometheus(
    host: str = None, port: int = None
):
    pass


def meter_provider_readers_pull(exporter: object):
    pass


def meter_provider_readers_pull_exporter(
    console: object = None,
    otlp: object = None,
    prometheus: object = None,
    **kwargs
):
    pass


def meter_provider_readers_pull_exporter_otlp(
    endpoint: str,
    protocol: str,
    certificate: str = None,
    client_certificate: str = None,
    client_key: str = None,
    compression: str = None,
    default_histogram_aggregation: str = None,
    headers: object = None,
    temporality_preference: str = None,
    timeout: int = None,
):
    pass


def meter_provider_readers_pull_exporter_otlp_headers(**kwargs):
    pass


def meter_provider_readers_pull_exporter_console():
    pass


def meter_provider_readers_pull_exporter_prometheus(
    host: str = None, port: int = None
):
    pass


def meter_provider_views(selector: object = None, stream: object = None):
    pass


def meter_provider_views_selector(
    instrument_name: str = None,
    instrument_type: str = None,
    meter_name: str = None,
    meter_schema_url: str = None,
    meter_version: str = None,
    unit: str = None,
):
    pass


def meter_provider_views_stream(
    aggregation: object = None,
    attribute_keys: list = None,
    description: str = None,
    name: str = None,
):
    pass


def meter_provider_views_stream_aggregation(
    base2_exponential_bucket_histogram: object = None,
    default: object = None,
    drop: object = None,
    explicit_bucket_histogram: object = None,
    last_value: object = None,
    sum: object = None,
):
    pass


def meter_provider_views_stream_aggregation_default():
    pass


def meter_provider_views_stream_aggregation_drop():
    pass


def meter_provider_views_stream_aggregation_explicit_bucket_histogram(
    boundaries: list = None, record_min_max: bool = None
):
    pass


def meter_provider_views_stream_aggregation_base2_exponential_bucket_histogram(
    max_scale: int = None, max_size: int = None, record_min_max: bool = None
):
    pass


def meter_provider_views_stream_aggregation_last_value():
    pass


def meter_provider_views_stream_aggregation_sum():
    pass


def propagator(composite: list = None, **kwargs):
    pass


def tracer_provider(
    limits: object = None, processors: list = None, sampler: object = None
):
    # FIXME how to define shutdown_on_exit?
    # FIXME how to define id_generator?
    # FIXME how to define if the span processors should be synchronous or not?

    synchronous_multi_span_processor = SynchronousMultiSpanProcessor()

    if processors is not None:
        for processor in processors:
            synchronous_multi_span_processor.add_span_processor(processor)

    return TracerProvider(
        sampler=sampler,
        resource=_resource,
        active_span_processor=synchronous_multi_span_processor,
        span_limits=limits,
    )


def tracer_provider_processors(
    batch: object = None, simple: object = None, **kwargs
):
    return batch or simple


def tracer_provider_processors_batch(
    exporter: object,
    export_timeout: int = None,
    max_export_batch_size: int = None,
    max_queue_size: int = None,
    schedule_delay: int = None,
):
    return BatchSpanProcessor(
        exporter,
        max_queue_size=max_queue_size,
        schedule_delay_millis=schedule_delay,
        max_export_batch_size=max_export_batch_size,
        export_timeout_millis=export_timeout,
    )


def tracer_provider_processors_batch_exporter(
    console: object = None,
    otlp: object = None,
    zipkin: object = None,
    **kwargs
):
    return console or otlp or zipkin


def tracer_provider_processors_batch_exporter_otlp(
    endpoint: str,
    protocol: str,
    certificate: str = None,
    client_certificate: str = None,
    client_key: str = None,
    compression: str = None,
    headers: object = None,
    timeout: int = None,
):
    protocol = urlparse(protocol).scheme

    if protocol.startswith("http"):
        exporter_class = HTTPOTLPSpanExporter

    else:
        exporter_class = GRPCOTLPSpanExporter

    return exporter_class(
        endpoint=endpoint,
        # insecure=None,
        # FIXME somehow create credentials here
        # from grpc.credentials import create_credentials
        # credentials=create_credentials()
        headers=headers,
        timeout=timeout,
        # compression=compression
    )


def tracer_provider_processors_batch_exporter_otlp_headers(**kwargs):
    return kwargs


def tracer_provider_processors_batch_exporter_console():
    return ConsoleSpanExporter
    pass


def tracer_provider_processors_batch_exporter_zipkin(
    endpoint: str, timeout: int = None
):
    return ZipkinExporter(endpoint, timeout=timeout)


def tracer_provider_processors_simple(exporter: object):
    return SimpleSpanProcessor(exporter)


def tracer_provider_processors_simple_exporter(
    console: object = None,
    otlp: object = None,
    zipkin: object = None,
    **kwargs
):
    return console or otlp or zipkin


def tracer_provider_processors_simple_exporter_otlp(
    endpoint: str,
    protocol: str,
    certificate: str = None,
    client_certificate: str = None,
    client_key: str = None,
    compression: str = None,
    headers: object = None,
    timeout: int = None,
):
    protocol = urlparse(protocol).scheme

    if protocol.startswith("http"):
        exporter_class = HTTPOTLPSpanExporter

    else:
        exporter_class = GRPCOTLPSpanExporter

    return exporter_class(
        endpoint=endpoint,
        # insecure=None,
        # FIXME somehow create credentials here
        # from grpc.credentials import create_credentials
        # credentials=create_credentials()
        headers=headers,
        timeout=timeout,
        # compression=compression
    )


def tracer_provider_processors_simple_exporter_otlp_headers(**kwargs):
    return kwargs


def tracer_provider_processors_simple_exporter_console():
    return ConsoleSpanExporter()


def tracer_provider_processors_simple_exporter_zipkin(
    endpoint: str, timeout: int = None
):
    return ZipkinExporter(endpoint, timeout=timeout)


def tracer_provider_limits(
    attribute_count_limit: int = None,
    attribute_value_length_limit: int = None,
    event_attribute_count_limit: int = None,
    event_count_limit: int = None,
    link_attribute_count_limit: int = None,
    link_count_limit: int = None,
):
    return SpanLimits(
        max_span_attributes=attribute_count_limit,
        max_span_attribute_length=attribute_value_length_limit,
        max_event_attributes=event_count_limit,
        max_events=event_count_limit,
        max_link_attributes=link_attribute_count_limit,
        max_links=link_count_limit,
    )


def tracer_provider_sampler(
    always_off: object = None,
    always_on: object = None,
    jaeger_remote: object = None,
    parent_based: object = None,
    trace_id_ratio_based: object = None,
    **kwargs
):
    return MockSampler(
        type="Sampler",
        always_off=always_off,
        always_on=always_on,
        jaeger_remote=jaeger_remote,
        parent_based=parent_based,
        trace_id_ratio_based=trace_id_ratio_based,
        **kwargs
    )


def tracer_provider_sampler_always_off():
    return ALWAYS_OFF


def tracer_provider_sampler_always_on():
    return ALWAYS_ON


def tracer_provider_sampler_jaeger_remote(
    endpoint: str = None, initial_sampler: object = None, interval: int = None
):
    return MockSampler(
        type="JaegerRemoteSampler",
        endpoint=endpoint,
        initial_sampler=initial_sampler,
        interval=interval,
    )


def tracer_provider_sampler_jaeger_remote_initial_sampler(
    always_off: object = None,
    always_on: object = None,
    jaeger_remote: object = None,
    parent_based: object = None,
    trace_id_ratio_based: object = None,
    **kwargs
):
    return MockSampler(
        type="InitialSamplerSampler",
        always_off=always_off,
        always_on=always_on,
        jaeger_remote=jaeger_remote,
        parent_based=parent_based,
        trace_id_ratio_based=trace_id_ratio_based,
        **kwargs
    )


def tracer_provider_sampler_parent_based(
    local_parent_not_sampled: object = None,
    local_parent_sampled: object = None,
    remote_parent_not_sampled: object = None,
    remote_parent_sampled: object = None,
    root: object = None,
):
    return MockSampler(
        type="ParentBasedSampler",
        local_parent_not_sampled=local_parent_not_sampled,
        local_parent_sampled=local_parent_sampled,
        remote_parent_not_sampled=remote_parent_not_sampled,
        remote_parent_sampled=remote_parent_sampled,
        root=root,
    )


def tracer_provider_sampler_parent_based_root(
    always_off: object = None,
    always_on: object = None,
    jaeger_remote: object = None,
    parent_based: object = None,
    trace_id_ratio_based: object = None,
    **kwargs
):
    return MockSampler(
        type="RootSampler",
        always_off=always_off,
        always_on=always_on,
        jaeger_remote=jaeger_remote,
        parent_based=parent_based,
        trace_id_ratio_based=trace_id_ratio_based,
        **kwargs
    )


def tracer_provider_sampler_parent_based_remote_parent_sampled(
    always_off: object = None,
    always_on: object = None,
    jaeger_remote: object = None,
    parent_based: object = None,
    trace_id_ratio_based: object = None,
    **kwargs
):
    return MockSampler(
        type="RemoteParentSampledSampler",
        always_off=always_off,
        always_on=always_on,
        jaeger_remote=jaeger_remote,
        parent_based=parent_based,
        trace_id_ratio_based=trace_id_ratio_based,
        **kwargs
    )


def tracer_provider_sampler_parent_based_remote_parent_not_sampled(
    always_off: object = None,
    always_on: object = None,
    jaeger_remote: object = None,
    parent_based: object = None,
    trace_id_ratio_based: object = None,
    **kwargs
):
    return MockSampler(
        type="RemoteParentNotSampledSampler",
        always_off=always_off,
        always_on=always_on,
        jaeger_remote=jaeger_remote,
        parent_based=parent_based,
        trace_id_ratio_based=trace_id_ratio_based,
        **kwargs
    )


def tracer_provider_sampler_parent_based_local_parent_sampled(
    always_off: object = None,
    always_on: object = None,
    jaeger_remote: object = None,
    parent_based: object = None,
    trace_id_ratio_based: object = None,
    **kwargs
):
    return MockSampler(
        type="LocalParentSampledSampler",
        always_off=always_off,
        always_on=always_on,
        jaeger_remote=jaeger_remote,
        parent_based=parent_based,
        trace_id_ratio_based=trace_id_ratio_based,
        **kwargs
    )


def tracer_provider_sampler_parent_based_local_parent_not_sampled(
    always_off: object = None,
    always_on: object = None,
    jaeger_remote: object = None,
    parent_based: object = None,
    trace_id_ratio_based: object = None,
    **kwargs
):
    return MockSampler(
        type="LocalParentNotSampledSampler",
        always_off=always_off,
        always_on=always_on,
        jaeger_remote=jaeger_remote,
        parent_based=parent_based,
        trace_id_ratio_based=trace_id_ratio_based,
        **kwargs
    )


def tracer_provider_sampler_trace_id_ratio_based(ratio: float = None):
    return ParentBasedTraceIdRatio(ratio)


def resource(attributes: object = None, schema_url: str = None):
    return Resource.create(attributes=attributes, schema_url=schema_url)


def resource_attributes(service_name: str = None, **kwargs):
    return {"service.name": service_name, **kwargs}


path_function = {
    "attribute_limits": {
        "function": attribute_limits,
        "children": {},
        "recursive_path": [],
    },
    "logger_provider": {
        "function": logger_provider,
        "children": {
            "processors": {
                "function": logger_provider_processors,
                "children": {
                    "batch": {
                        "function": logger_provider_processors_batch,
                        "children": {
                            "exporter": {
                                "function": logger_provider_processors_batch_exporter,  # noqa
                                "children": {
                                    "otlp": {
                                        "function": logger_provider_processors_batch_exporter_otlp,  # noqa
                                        "children": {
                                            "headers": {
                                                "function": logger_provider_processors_batch_exporter_otlp_headers,  # noqa
                                                "children": {},
                                                "recursive_path": [],
                                            },
                                        },
                                        "recursive_path": [],
                                    },
                                },
                                "recursive_path": [],
                            },
                        },
                        "recursive_path": [],
                    },
                    "simple": {
                        "function": logger_provider_processors_simple,
                        "children": {
                            "exporter": {
                                "function": logger_provider_processors_simple_exporter,  # noqa
                                "children": {
                                    "otlp": {
                                        "function": logger_provider_processors_simple_exporter_otlp,  # noqa
                                        "children": {
                                            "headers": {
                                                "function": logger_provider_processors_simple_exporter_otlp_headers,  # noqa
                                                "children": {},
                                                "recursive_path": [],
                                            },
                                        },
                                        "recursive_path": [],
                                    },
                                },
                                "recursive_path": [],
                            },
                        },
                        "recursive_path": [],
                    },
                },
                "recursive_path": [],
            },
            "limits": {
                "function": logger_provider_limits,
                "children": {},
                "recursive_path": [],
            },
        },
        "recursive_path": [],
    },
    "meter_provider": {
        "function": meter_provider,
        "children": {
            "readers": {
                "function": meter_provider_readers,
                "children": {
                    "periodic": {
                        "function": meter_provider_readers_periodic,
                        "children": {
                            "exporter": {
                                "function": meter_provider_readers_periodic_exporter,  # noqa
                                "children": {
                                    "otlp": {
                                        "function": meter_provider_readers_periodic_exporter_otlp,  # noqa
                                        "children": {
                                            "headers": {
                                                "function": meter_provider_readers_periodic_exporter_otlp_headers,  # noqa
                                                "children": {},
                                                "recursive_path": [],
                                            },
                                        },
                                        "recursive_path": [],
                                    },
                                    "console": {
                                        "function": meter_provider_readers_periodic_exporter_console,  # noqa
                                        "children": {},
                                        "recursive_path": [],
                                    },
                                    "prometheus": {
                                        "function": meter_provider_readers_periodic_exporter_prometheus,  # noqa
                                        "children": {},
                                        "recursive_path": [],
                                    },
                                },
                                "recursive_path": [],
                            },
                        },
                        "recursive_path": [],
                    },
                    "pull": {
                        "function": meter_provider_readers_pull,
                        "children": {
                            "exporter": {
                                "function": meter_provider_readers_pull_exporter,  # noqa
                                "children": {
                                    "otlp": {
                                        "function": meter_provider_readers_pull_exporter_otlp,  # noqa
                                        "children": {
                                            "headers": {
                                                "function": meter_provider_readers_pull_exporter_otlp_headers,  # noqa
                                                "children": {},
                                                "recursive_path": [],
                                            },
                                        },
                                        "recursive_path": [],
                                    },
                                    "console": {
                                        "function": meter_provider_readers_pull_exporter_console,  # noqa
                                        "children": {},
                                        "recursive_path": [],
                                    },
                                    "prometheus": {
                                        "function": meter_provider_readers_pull_exporter_prometheus,  # noqa
                                        "children": {},
                                        "recursive_path": [],
                                    },
                                },
                                "recursive_path": [],
                            },
                        },
                        "recursive_path": [],
                    },
                },
                "recursive_path": [],
            },
            "views": {
                "function": meter_provider_views,
                "children": {
                    "selector": {
                        "function": meter_provider_views_selector,
                        "children": {},
                        "recursive_path": [],
                    },
                    "stream": {
                        "function": meter_provider_views_stream,
                        "children": {
                            "aggregation": {
                                "function": meter_provider_views_stream_aggregation,  # noqa
                                "children": {
                                    "default": {
                                        "function": meter_provider_views_stream_aggregation_default,  # noqa
                                        "children": {},
                                        "recursive_path": [],
                                    },
                                    "drop": {
                                        "function": meter_provider_views_stream_aggregation_drop,  # noqa
                                        "children": {},
                                        "recursive_path": [],
                                    },
                                    "explicit_bucket_histogram": {
                                        "function": meter_provider_views_stream_aggregation_explicit_bucket_histogram,  # noqa
                                        "children": {},
                                        "recursive_path": [],
                                    },
                                    "base2_exponential_bucket_histogram": {
                                        "function": meter_provider_views_stream_aggregation_base2_exponential_bucket_histogram,  # noqa
                                        "children": {},
                                        "recursive_path": [],
                                    },
                                    "last_value": {
                                        "function": meter_provider_views_stream_aggregation_last_value,  # noqa
                                        "children": {},
                                        "recursive_path": [],
                                    },
                                    "sum": {
                                        "function": meter_provider_views_stream_aggregation_sum,  # noqa
                                        "children": {},
                                        "recursive_path": [],
                                    },
                                },
                                "recursive_path": [],
                            },
                        },
                        "recursive_path": [],
                    },
                },
                "recursive_path": [],
            },
        },
        "recursive_path": [],
    },
    "propagator": {
        "function": propagator,
        "children": {},
        "recursive_path": [],
    },
    "tracer_provider": {
        "function": tracer_provider,
        "children": {
            "processors": {
                "function": tracer_provider_processors,
                "children": {
                    "batch": {
                        "function": tracer_provider_processors_batch,
                        "children": {
                            "exporter": {
                                "function": tracer_provider_processors_batch_exporter,  # noqa
                                "children": {
                                    "otlp": {
                                        "function": tracer_provider_processors_batch_exporter_otlp,  # noqa
                                        "children": {
                                            "headers": {
                                                "function": tracer_provider_processors_batch_exporter_otlp_headers,  # noqa
                                                "children": {},
                                                "recursive_path": [],
                                            },
                                        },
                                        "recursive_path": [],
                                    },
                                    "console": {
                                        "function": tracer_provider_processors_batch_exporter_console,  # noqa
                                        "children": {},
                                        "recursive_path": [],
                                    },
                                    "zipkin": {
                                        "function": tracer_provider_processors_batch_exporter_zipkin,  # noqa
                                        "children": {},
                                        "recursive_path": [],
                                    },
                                },
                                "recursive_path": [],
                            },
                        },
                        "recursive_path": [],
                    },
                    "simple": {
                        "function": tracer_provider_processors_simple,
                        "children": {
                            "exporter": {
                                "function": tracer_provider_processors_simple_exporter,  # noqa
                                "children": {
                                    "otlp": {
                                        "function": tracer_provider_processors_simple_exporter_otlp,  # noqa
                                        "children": {
                                            "headers": {
                                                "function": tracer_provider_processors_simple_exporter_otlp_headers,  # noqa
                                                "children": {},
                                                "recursive_path": [],
                                            },
                                        },
                                        "recursive_path": [],
                                    },
                                    "console": {
                                        "function": tracer_provider_processors_simple_exporter_console,  # noqa
                                        "children": {},
                                        "recursive_path": [],
                                    },
                                    "zipkin": {
                                        "function": tracer_provider_processors_simple_exporter_zipkin,  # noqa
                                        "children": {},
                                        "recursive_path": [],
                                    },
                                },
                                "recursive_path": [],
                            },
                        },
                        "recursive_path": [],
                    },
                },
                "recursive_path": [],
            },
            "limits": {
                "function": tracer_provider_limits,
                "children": {},
                "recursive_path": [],
            },
            "sampler": {
                "function": tracer_provider_sampler,
                "children": {
                    "always_off": {
                        "function": tracer_provider_sampler_always_off,
                        "children": {},
                        "recursive_path": [],
                    },
                    "always_on": {
                        "function": tracer_provider_sampler_always_on,
                        "children": {},
                        "recursive_path": [],
                    },
                    "jaeger_remote": {
                        "function": tracer_provider_sampler_jaeger_remote,
                        "children": {
                            "initial_sampler": {
                                "function": tracer_provider_sampler_jaeger_remote_initial_sampler,  # noqa
                                "children": {},
                                "recursive_path": [
                                    "tracer_provider",
                                    "sampler",
                                ],  # noqa
                            },
                        },
                        "recursive_path": [],
                    },
                    "parent_based": {
                        "function": tracer_provider_sampler_parent_based,
                        "children": {
                            "root": {
                                "function": tracer_provider_sampler_parent_based_root,  # noqa
                                "children": {},
                                "recursive_path": [
                                    "tracer_provider",
                                    "sampler",
                                ],  # noqa
                            },
                            "remote_parent_sampled": {
                                "function": tracer_provider_sampler_parent_based_remote_parent_sampled,  # noqa
                                "children": {},
                                "recursive_path": [
                                    "tracer_provider",
                                    "sampler",
                                ],  # noqa
                            },
                            "remote_parent_not_sampled": {
                                "function": tracer_provider_sampler_parent_based_remote_parent_not_sampled,  # noqa
                                "children": {},
                                "recursive_path": [
                                    "tracer_provider",
                                    "sampler",
                                ],  # noqa
                            },
                            "local_parent_sampled": {
                                "function": tracer_provider_sampler_parent_based_local_parent_sampled,  # noqa
                                "children": {},
                                "recursive_path": [
                                    "tracer_provider",
                                    "sampler",
                                ],  # noqa
                            },
                            "local_parent_not_sampled": {
                                "function": tracer_provider_sampler_parent_based_local_parent_not_sampled,  # noqa
                                "children": {},
                                "recursive_path": [
                                    "tracer_provider",
                                    "sampler",
                                ],  # noqa
                            },
                        },
                        "recursive_path": [],
                    },
                    "trace_id_ratio_based": {
                        "function": tracer_provider_sampler_trace_id_ratio_based,  # noqa
                        "children": {},
                        "recursive_path": [],
                    },
                },
                "recursive_path": [],
            },
        },
        "recursive_path": [],
    },
    "resource": {
        "function": resource,
        "children": {
            "attributes": {
                "function": resource_attributes,
                "children": {},
                "recursive_path": [],
            },
        },
        "recursive_path": [],
    },
}
