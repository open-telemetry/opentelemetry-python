from google.protobuf.internal.api_implementation import Type as _Type
if _Type() == "upb":
  # -*- coding: utf-8 -*-
  # Generated by the protocol buffer compiler.  DO NOT EDIT!
  # source: opentelemetry/proto/collector/trace/v1/trace_service.proto
  """Generated protocol buffer code."""
  from google.protobuf.internal import builder as _builder
  from google.protobuf import descriptor as _descriptor
  from google.protobuf import descriptor_pool as _descriptor_pool
  from google.protobuf import symbol_database as _symbol_database
  # @@protoc_insertion_point(imports)
  
  _sym_db = _symbol_database.Default()
  
  
  from opentelemetry.proto.trace.v1 import trace_pb2 as opentelemetry_dot_proto_dot_trace_dot_v1_dot_trace__pb2
  
  
  DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n:opentelemetry/proto/collector/trace/v1/trace_service.proto\x12&opentelemetry.proto.collector.trace.v1\x1a(opentelemetry/proto/trace/v1/trace.proto\"`\n\x19\x45xportTraceServiceRequest\x12\x43\n\x0eresource_spans\x18\x01 \x03(\x0b\x32+.opentelemetry.proto.trace.v1.ResourceSpans\"\x1c\n\x1a\x45xportTraceServiceResponse2\xa2\x01\n\x0cTraceService\x12\x91\x01\n\x06\x45xport\x12\x41.opentelemetry.proto.collector.trace.v1.ExportTraceServiceRequest\x1a\x42.opentelemetry.proto.collector.trace.v1.ExportTraceServiceResponse\"\x00\x42s\n)io.opentelemetry.proto.collector.trace.v1B\x11TraceServiceProtoP\x01Z1go.opentelemetry.io/proto/otlp/collector/trace/v1b\x06proto3')
  
  _builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
  _builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'opentelemetry.proto.collector.trace.v1.trace_service_pb2', globals())
  if _descriptor._USE_C_DESCRIPTORS == False:
  
    DESCRIPTOR._options = None
    DESCRIPTOR._serialized_options = b'\n)io.opentelemetry.proto.collector.trace.v1B\021TraceServiceProtoP\001Z1go.opentelemetry.io/proto/otlp/collector/trace/v1'
    _EXPORTTRACESERVICEREQUEST._serialized_start=144
    _EXPORTTRACESERVICEREQUEST._serialized_end=240
    _EXPORTTRACESERVICERESPONSE._serialized_start=242
    _EXPORTTRACESERVICERESPONSE._serialized_end=270
    _TRACESERVICE._serialized_start=273
    _TRACESERVICE._serialized_end=435
  # @@protoc_insertion_point(module_scope)
else:
  # -*- coding: utf-8 -*-
  # Generated by the protocol buffer compiler.  DO NOT EDIT!
  # source: opentelemetry/proto/collector/trace/v1/trace_service.proto
  """Generated protocol buffer code."""
  from google.protobuf import descriptor as _descriptor
  from google.protobuf import message as _message
  from google.protobuf import reflection as _reflection
  from google.protobuf import symbol_database as _symbol_database
  # @@protoc_insertion_point(imports)
  
  _sym_db = _symbol_database.Default()
  
  
  from opentelemetry.proto.trace.v1 import trace_pb2 as opentelemetry_dot_proto_dot_trace_dot_v1_dot_trace__pb2
  
  
  DESCRIPTOR = _descriptor.FileDescriptor(
    name='opentelemetry/proto/collector/trace/v1/trace_service.proto',
    package='opentelemetry.proto.collector.trace.v1',
    syntax='proto3',
    serialized_options=b'\n)io.opentelemetry.proto.collector.trace.v1B\021TraceServiceProtoP\001Z1go.opentelemetry.io/proto/otlp/collector/trace/v1',
    create_key=_descriptor._internal_create_key,
    serialized_pb=b'\n:opentelemetry/proto/collector/trace/v1/trace_service.proto\x12&opentelemetry.proto.collector.trace.v1\x1a(opentelemetry/proto/trace/v1/trace.proto\"`\n\x19\x45xportTraceServiceRequest\x12\x43\n\x0eresource_spans\x18\x01 \x03(\x0b\x32+.opentelemetry.proto.trace.v1.ResourceSpans\"\x1c\n\x1a\x45xportTraceServiceResponse2\xa2\x01\n\x0cTraceService\x12\x91\x01\n\x06\x45xport\x12\x41.opentelemetry.proto.collector.trace.v1.ExportTraceServiceRequest\x1a\x42.opentelemetry.proto.collector.trace.v1.ExportTraceServiceResponse\"\x00\x42s\n)io.opentelemetry.proto.collector.trace.v1B\x11TraceServiceProtoP\x01Z1go.opentelemetry.io/proto/otlp/collector/trace/v1b\x06proto3'
    ,
    dependencies=[opentelemetry_dot_proto_dot_trace_dot_v1_dot_trace__pb2.DESCRIPTOR,])
  
  
  
  
  _EXPORTTRACESERVICEREQUEST = _descriptor.Descriptor(
    name='ExportTraceServiceRequest',
    full_name='opentelemetry.proto.collector.trace.v1.ExportTraceServiceRequest',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
      _descriptor.FieldDescriptor(
        name='resource_spans', full_name='opentelemetry.proto.collector.trace.v1.ExportTraceServiceRequest.resource_spans', index=0,
        number=1, type=11, cpp_type=10, label=3,
        has_default_value=False, default_value=[],
        message_type=None, enum_type=None, containing_type=None,
        is_extension=False, extension_scope=None,
        serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
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
    serialized_start=144,
    serialized_end=240,
  )
  
  
  _EXPORTTRACESERVICERESPONSE = _descriptor.Descriptor(
    name='ExportTraceServiceResponse',
    full_name='opentelemetry.proto.collector.trace.v1.ExportTraceServiceResponse',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
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
    serialized_start=242,
    serialized_end=270,
  )
  
  _EXPORTTRACESERVICEREQUEST.fields_by_name['resource_spans'].message_type = opentelemetry_dot_proto_dot_trace_dot_v1_dot_trace__pb2._RESOURCESPANS
  DESCRIPTOR.message_types_by_name['ExportTraceServiceRequest'] = _EXPORTTRACESERVICEREQUEST
  DESCRIPTOR.message_types_by_name['ExportTraceServiceResponse'] = _EXPORTTRACESERVICERESPONSE
  _sym_db.RegisterFileDescriptor(DESCRIPTOR)
  
  ExportTraceServiceRequest = _reflection.GeneratedProtocolMessageType('ExportTraceServiceRequest', (_message.Message,), {
    'DESCRIPTOR' : _EXPORTTRACESERVICEREQUEST,
    '__module__' : 'opentelemetry.proto.collector.trace.v1.trace_service_pb2'
    # @@protoc_insertion_point(class_scope:opentelemetry.proto.collector.trace.v1.ExportTraceServiceRequest)
    })
  _sym_db.RegisterMessage(ExportTraceServiceRequest)
  
  ExportTraceServiceResponse = _reflection.GeneratedProtocolMessageType('ExportTraceServiceResponse', (_message.Message,), {
    'DESCRIPTOR' : _EXPORTTRACESERVICERESPONSE,
    '__module__' : 'opentelemetry.proto.collector.trace.v1.trace_service_pb2'
    # @@protoc_insertion_point(class_scope:opentelemetry.proto.collector.trace.v1.ExportTraceServiceResponse)
    })
  _sym_db.RegisterMessage(ExportTraceServiceResponse)
  
  
  DESCRIPTOR._options = None
  
  _TRACESERVICE = _descriptor.ServiceDescriptor(
    name='TraceService',
    full_name='opentelemetry.proto.collector.trace.v1.TraceService',
    file=DESCRIPTOR,
    index=0,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
    serialized_start=273,
    serialized_end=435,
    methods=[
    _descriptor.MethodDescriptor(
      name='Export',
      full_name='opentelemetry.proto.collector.trace.v1.TraceService.Export',
      index=0,
      containing_service=None,
      input_type=_EXPORTTRACESERVICEREQUEST,
      output_type=_EXPORTTRACESERVICERESPONSE,
      serialized_options=None,
      create_key=_descriptor._internal_create_key,
    ),
  ])
  _sym_db.RegisterServiceDescriptor(_TRACESERVICE)
  
  DESCRIPTOR.services_by_name['TraceService'] = _TRACESERVICE
  
  # @@protoc_insertion_point(module_scope)
