# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: opentelemetry/proto/trace/v1/trace_config.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n/opentelemetry/proto/trace/v1/trace_config.proto\x12\x1copentelemetry.proto.trace.v1\"\xc8\x03\n\x0bTraceConfig\x12I\n\x10\x63onstant_sampler\x18\x01 \x01(\x0b\x32-.opentelemetry.proto.trace.v1.ConstantSamplerH\x00\x12O\n\x14trace_id_ratio_based\x18\x02 \x01(\x0b\x32/.opentelemetry.proto.trace.v1.TraceIdRatioBasedH\x00\x12R\n\x15rate_limiting_sampler\x18\x03 \x01(\x0b\x32\x31.opentelemetry.proto.trace.v1.RateLimitingSamplerH\x00\x12 \n\x18max_number_of_attributes\x18\x04 \x01(\x03\x12\"\n\x1amax_number_of_timed_events\x18\x05 \x01(\x03\x12\x30\n(max_number_of_attributes_per_timed_event\x18\x06 \x01(\x03\x12\x1b\n\x13max_number_of_links\x18\x07 \x01(\x03\x12)\n!max_number_of_attributes_per_link\x18\x08 \x01(\x03\x42\t\n\x07sampler\"\xa9\x01\n\x0f\x43onstantSampler\x12P\n\x08\x64\x65\x63ision\x18\x01 \x01(\x0e\x32>.opentelemetry.proto.trace.v1.ConstantSampler.ConstantDecision\"D\n\x10\x43onstantDecision\x12\x0e\n\nALWAYS_OFF\x10\x00\x12\r\n\tALWAYS_ON\x10\x01\x12\x11\n\rALWAYS_PARENT\x10\x02\"*\n\x11TraceIdRatioBased\x12\x15\n\rsamplingRatio\x18\x01 \x01(\x01\"\"\n\x13RateLimitingSampler\x12\x0b\n\x03qps\x18\x01 \x01(\x03\x42h\n\x1fio.opentelemetry.proto.trace.v1B\x10TraceConfigProtoP\x01Z1go.opentelemetry.io/proto/otlp/collector/trace/v1b\x06proto3')



_TRACECONFIG = DESCRIPTOR.message_types_by_name['TraceConfig']
_CONSTANTSAMPLER = DESCRIPTOR.message_types_by_name['ConstantSampler']
_TRACEIDRATIOBASED = DESCRIPTOR.message_types_by_name['TraceIdRatioBased']
_RATELIMITINGSAMPLER = DESCRIPTOR.message_types_by_name['RateLimitingSampler']
_CONSTANTSAMPLER_CONSTANTDECISION = _CONSTANTSAMPLER.enum_types_by_name['ConstantDecision']
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

if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  DESCRIPTOR._serialized_options = b'\n\037io.opentelemetry.proto.trace.v1B\020TraceConfigProtoP\001Z1go.opentelemetry.io/proto/otlp/collector/trace/v1'
  _TRACECONFIG._serialized_start=82
  _TRACECONFIG._serialized_end=538
  _CONSTANTSAMPLER._serialized_start=541
  _CONSTANTSAMPLER._serialized_end=710
  _CONSTANTSAMPLER_CONSTANTDECISION._serialized_start=642
  _CONSTANTSAMPLER_CONSTANTDECISION._serialized_end=710
  _TRACEIDRATIOBASED._serialized_start=712
  _TRACEIDRATIOBASED._serialized_end=754
  _RATELIMITINGSAMPLER._serialized_start=756
  _RATELIMITINGSAMPLER._serialized_end=790
# @@protoc_insertion_point(module_scope)
