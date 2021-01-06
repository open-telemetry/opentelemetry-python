# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: opentelemetry/proto/trace/v1/trace_config.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='opentelemetry/proto/trace/v1/trace_config.proto',
  package='opentelemetry.proto.trace.v1',
  syntax='proto3',
  serialized_options=b'\n\037io.opentelemetry.proto.trace.v1B\020TraceConfigProtoP\001ZGgithub.com/open-telemetry/opentelemetry-proto/gen/go/collector/trace/v1',
  serialized_pb=b'\n/opentelemetry/proto/trace/v1/trace_config.proto\x12\x1copentelemetry.proto.trace.v1\"\xc8\x03\n\x0bTraceConfig\x12I\n\x10\x63onstant_sampler\x18\x01 \x01(\x0b\x32-.opentelemetry.proto.trace.v1.ConstantSamplerH\x00\x12O\n\x14trace_id_ratio_based\x18\x02 \x01(\x0b\x32/.opentelemetry.proto.trace.v1.TraceIdRatioBasedH\x00\x12R\n\x15rate_limiting_sampler\x18\x03 \x01(\x0b\x32\x31.opentelemetry.proto.trace.v1.RateLimitingSamplerH\x00\x12 \n\x18max_number_of_attributes\x18\x04 \x01(\x03\x12\"\n\x1amax_number_of_timed_events\x18\x05 \x01(\x03\x12\x30\n(max_number_of_attributes_per_timed_event\x18\x06 \x01(\x03\x12\x1b\n\x13max_number_of_links\x18\x07 \x01(\x03\x12)\n!max_number_of_attributes_per_link\x18\x08 \x01(\x03\x42\t\n\x07sampler\"\xa9\x01\n\x0f\x43onstantSampler\x12P\n\x08\x64\x65\x63ision\x18\x01 \x01(\x0e\x32>.opentelemetry.proto.trace.v1.ConstantSampler.ConstantDecision\"D\n\x10\x43onstantDecision\x12\x0e\n\nALWAYS_OFF\x10\x00\x12\r\n\tALWAYS_ON\x10\x01\x12\x11\n\rALWAYS_PARENT\x10\x02\"*\n\x11TraceIdRatioBased\x12\x15\n\rsamplingRatio\x18\x01 \x01(\x01\"\"\n\x13RateLimitingSampler\x12\x0b\n\x03qps\x18\x01 \x01(\x03\x42~\n\x1fio.opentelemetry.proto.trace.v1B\x10TraceConfigProtoP\x01ZGgithub.com/open-telemetry/opentelemetry-proto/gen/go/collector/trace/v1b\x06proto3'
)



_CONSTANTSAMPLER_CONSTANTDECISION = _descriptor.EnumDescriptor(
  name='ConstantDecision',
  full_name='opentelemetry.proto.trace.v1.ConstantSampler.ConstantDecision',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='ALWAYS_OFF', index=0, number=0,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ALWAYS_ON', index=1, number=1,
      serialized_options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ALWAYS_PARENT', index=2, number=2,
      serialized_options=None,
      type=None),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=642,
  serialized_end=710,
)
_sym_db.RegisterEnumDescriptor(_CONSTANTSAMPLER_CONSTANTDECISION)


_TRACECONFIG = _descriptor.Descriptor(
  name='TraceConfig',
  full_name='opentelemetry.proto.trace.v1.TraceConfig',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='constant_sampler', full_name='opentelemetry.proto.trace.v1.TraceConfig.constant_sampler', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='trace_id_ratio_based', full_name='opentelemetry.proto.trace.v1.TraceConfig.trace_id_ratio_based', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='rate_limiting_sampler', full_name='opentelemetry.proto.trace.v1.TraceConfig.rate_limiting_sampler', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='max_number_of_attributes', full_name='opentelemetry.proto.trace.v1.TraceConfig.max_number_of_attributes', index=3,
      number=4, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='max_number_of_timed_events', full_name='opentelemetry.proto.trace.v1.TraceConfig.max_number_of_timed_events', index=4,
      number=5, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='max_number_of_attributes_per_timed_event', full_name='opentelemetry.proto.trace.v1.TraceConfig.max_number_of_attributes_per_timed_event', index=5,
      number=6, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='max_number_of_links', full_name='opentelemetry.proto.trace.v1.TraceConfig.max_number_of_links', index=6,
      number=7, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='max_number_of_attributes_per_link', full_name='opentelemetry.proto.trace.v1.TraceConfig.max_number_of_attributes_per_link', index=7,
      number=8, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
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
    _descriptor.OneofDescriptor(
      name='sampler', full_name='opentelemetry.proto.trace.v1.TraceConfig.sampler',
      index=0, containing_type=None, fields=[]),
  ],
  serialized_start=82,
  serialized_end=538,
)


_CONSTANTSAMPLER = _descriptor.Descriptor(
  name='ConstantSampler',
  full_name='opentelemetry.proto.trace.v1.ConstantSampler',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='decision', full_name='opentelemetry.proto.trace.v1.ConstantSampler.decision', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _CONSTANTSAMPLER_CONSTANTDECISION,
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=541,
  serialized_end=710,
)


_TRACEIDRATIOBASED = _descriptor.Descriptor(
  name='TraceIdRatioBased',
  full_name='opentelemetry.proto.trace.v1.TraceIdRatioBased',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='samplingRatio', full_name='opentelemetry.proto.trace.v1.TraceIdRatioBased.samplingRatio', index=0,
      number=1, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
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
  serialized_start=712,
  serialized_end=754,
)


_RATELIMITINGSAMPLER = _descriptor.Descriptor(
  name='RateLimitingSampler',
  full_name='opentelemetry.proto.trace.v1.RateLimitingSampler',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='qps', full_name='opentelemetry.proto.trace.v1.RateLimitingSampler.qps', index=0,
      number=1, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
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
  serialized_start=756,
  serialized_end=790,
)

_TRACECONFIG.fields_by_name['constant_sampler'].message_type = _CONSTANTSAMPLER
_TRACECONFIG.fields_by_name['trace_id_ratio_based'].message_type = _TRACEIDRATIOBASED
_TRACECONFIG.fields_by_name['rate_limiting_sampler'].message_type = _RATELIMITINGSAMPLER
_TRACECONFIG.oneofs_by_name['sampler'].fields.append(
  _TRACECONFIG.fields_by_name['constant_sampler'])
_TRACECONFIG.fields_by_name['constant_sampler'].containing_oneof = _TRACECONFIG.oneofs_by_name['sampler']
_TRACECONFIG.oneofs_by_name['sampler'].fields.append(
  _TRACECONFIG.fields_by_name['trace_id_ratio_based'])
_TRACECONFIG.fields_by_name['trace_id_ratio_based'].containing_oneof = _TRACECONFIG.oneofs_by_name['sampler']
_TRACECONFIG.oneofs_by_name['sampler'].fields.append(
  _TRACECONFIG.fields_by_name['rate_limiting_sampler'])
_TRACECONFIG.fields_by_name['rate_limiting_sampler'].containing_oneof = _TRACECONFIG.oneofs_by_name['sampler']
_CONSTANTSAMPLER.fields_by_name['decision'].enum_type = _CONSTANTSAMPLER_CONSTANTDECISION
_CONSTANTSAMPLER_CONSTANTDECISION.containing_type = _CONSTANTSAMPLER
DESCRIPTOR.message_types_by_name['TraceConfig'] = _TRACECONFIG
DESCRIPTOR.message_types_by_name['ConstantSampler'] = _CONSTANTSAMPLER
DESCRIPTOR.message_types_by_name['TraceIdRatioBased'] = _TRACEIDRATIOBASED
DESCRIPTOR.message_types_by_name['RateLimitingSampler'] = _RATELIMITINGSAMPLER
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

TraceConfig = _reflection.GeneratedProtocolMessageType('TraceConfig', (_message.Message,), {
  'DESCRIPTOR' : _TRACECONFIG,
  '__module__' : 'opentelemetry.proto.trace.v1.trace_config_pb2'
  # @@protoc_insertion_point(class_scope:opentelemetry.proto.trace.v1.TraceConfig)
  })
_sym_db.RegisterMessage(TraceConfig)

ConstantSampler = _reflection.GeneratedProtocolMessageType('ConstantSampler', (_message.Message,), {
  'DESCRIPTOR' : _CONSTANTSAMPLER,
  '__module__' : 'opentelemetry.proto.trace.v1.trace_config_pb2'
  # @@protoc_insertion_point(class_scope:opentelemetry.proto.trace.v1.ConstantSampler)
  })
_sym_db.RegisterMessage(ConstantSampler)

TraceIdRatioBased = _reflection.GeneratedProtocolMessageType('TraceIdRatioBased', (_message.Message,), {
  'DESCRIPTOR' : _TRACEIDRATIOBASED,
  '__module__' : 'opentelemetry.proto.trace.v1.trace_config_pb2'
  # @@protoc_insertion_point(class_scope:opentelemetry.proto.trace.v1.TraceIdRatioBased)
  })
_sym_db.RegisterMessage(TraceIdRatioBased)

RateLimitingSampler = _reflection.GeneratedProtocolMessageType('RateLimitingSampler', (_message.Message,), {
  'DESCRIPTOR' : _RATELIMITINGSAMPLER,
  '__module__' : 'opentelemetry.proto.trace.v1.trace_config_pb2'
  # @@protoc_insertion_point(class_scope:opentelemetry.proto.trace.v1.RateLimitingSampler)
  })
_sym_db.RegisterMessage(RateLimitingSampler)


DESCRIPTOR._options = None
# @@protoc_insertion_point(module_scope)
