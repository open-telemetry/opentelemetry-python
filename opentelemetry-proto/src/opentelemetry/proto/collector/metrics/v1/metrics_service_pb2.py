# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: opentelemetry/proto/collector/metrics/v1/metrics_service.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from opentelemetry.proto.metrics.v1 import metrics_pb2 as opentelemetry_dot_proto_dot_metrics_dot_v1_dot_metrics__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='opentelemetry/proto/collector/metrics/v1/metrics_service.proto',
  package='opentelemetry.proto.collector.metrics.v1',
  syntax='proto3',
  serialized_options=b'\n+io.opentelemetry.proto.collector.metrics.v1B\023MetricsServiceProtoP\001ZIgithub.com/open-telemetry/opentelemetry-proto/gen/go/collector/metrics/v1',
  serialized_pb=b'\n>opentelemetry/proto/collector/metrics/v1/metrics_service.proto\x12(opentelemetry.proto.collector.metrics.v1\x1a,opentelemetry/proto/metrics/v1/metrics.proto\"h\n\x1b\x45xportMetricsServiceRequest\x12I\n\x10resource_metrics\x18\x01 \x03(\x0b\x32/.opentelemetry.proto.metrics.v1.ResourceMetrics\"\x1e\n\x1c\x45xportMetricsServiceResponse2\xac\x01\n\x0eMetricsService\x12\x99\x01\n\x06\x45xport\x12\x45.opentelemetry.proto.collector.metrics.v1.ExportMetricsServiceRequest\x1a\x46.opentelemetry.proto.collector.metrics.v1.ExportMetricsServiceResponse\"\x00\x42\x8f\x01\n+io.opentelemetry.proto.collector.metrics.v1B\x13MetricsServiceProtoP\x01ZIgithub.com/open-telemetry/opentelemetry-proto/gen/go/collector/metrics/v1b\x06proto3'
  ,
  dependencies=[opentelemetry_dot_proto_dot_metrics_dot_v1_dot_metrics__pb2.DESCRIPTOR,])




_EXPORTMETRICSSERVICEREQUEST = _descriptor.Descriptor(
  name='ExportMetricsServiceRequest',
  full_name='opentelemetry.proto.collector.metrics.v1.ExportMetricsServiceRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='resource_metrics', full_name='opentelemetry.proto.collector.metrics.v1.ExportMetricsServiceRequest.resource_metrics', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=154,
  serialized_end=258,
)


_EXPORTMETRICSSERVICERESPONSE = _descriptor.Descriptor(
  name='ExportMetricsServiceResponse',
  full_name='opentelemetry.proto.collector.metrics.v1.ExportMetricsServiceResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=260,
  serialized_end=290,
)

_EXPORTMETRICSSERVICEREQUEST.fields_by_name['resource_metrics'].message_type = opentelemetry_dot_proto_dot_metrics_dot_v1_dot_metrics__pb2._RESOURCEMETRICS
DESCRIPTOR.message_types_by_name['ExportMetricsServiceRequest'] = _EXPORTMETRICSSERVICEREQUEST
DESCRIPTOR.message_types_by_name['ExportMetricsServiceResponse'] = _EXPORTMETRICSSERVICERESPONSE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

ExportMetricsServiceRequest = _reflection.GeneratedProtocolMessageType('ExportMetricsServiceRequest', (_message.Message,), {
  'DESCRIPTOR' : _EXPORTMETRICSSERVICEREQUEST,
  '__module__' : 'opentelemetry.proto.collector.metrics.v1.metrics_service_pb2'
  # @@protoc_insertion_point(class_scope:opentelemetry.proto.collector.metrics.v1.ExportMetricsServiceRequest)
  })
_sym_db.RegisterMessage(ExportMetricsServiceRequest)

ExportMetricsServiceResponse = _reflection.GeneratedProtocolMessageType('ExportMetricsServiceResponse', (_message.Message,), {
  'DESCRIPTOR' : _EXPORTMETRICSSERVICERESPONSE,
  '__module__' : 'opentelemetry.proto.collector.metrics.v1.metrics_service_pb2'
  # @@protoc_insertion_point(class_scope:opentelemetry.proto.collector.metrics.v1.ExportMetricsServiceResponse)
  })
_sym_db.RegisterMessage(ExportMetricsServiceResponse)


DESCRIPTOR._options = None

_METRICSSERVICE = _descriptor.ServiceDescriptor(
  name='MetricsService',
  full_name='opentelemetry.proto.collector.metrics.v1.MetricsService',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  serialized_start=293,
  serialized_end=465,
  methods=[
  _descriptor.MethodDescriptor(
    name='Export',
    full_name='opentelemetry.proto.collector.metrics.v1.MetricsService.Export',
    index=0,
    containing_service=None,
    input_type=_EXPORTMETRICSSERVICEREQUEST,
    output_type=_EXPORTMETRICSSERVICERESPONSE,
    serialized_options=None,
  ),
])
_sym_db.RegisterServiceDescriptor(_METRICSSERVICE)

DESCRIPTOR.services_by_name['MetricsService'] = _METRICSSERVICE

# @@protoc_insertion_point(module_scope)
