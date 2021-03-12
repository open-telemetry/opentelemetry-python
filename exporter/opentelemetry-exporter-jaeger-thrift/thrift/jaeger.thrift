# Copyright (c) 2016 Uber Technologies, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

namespace cpp jaegertracing.thrift
namespace java io.jaegertracing.thriftjava
namespace php Jaeger.Thrift
namespace netcore Jaeger.Thrift
namespace lua jaeger.thrift

# TagType denotes the type of a Tag's value.
enum TagType { STRING, DOUBLE, BOOL, LONG, BINARY }

# Tag is a basic strongly typed key/value pair. It has been flattened to reduce the use of pointers in golang
struct Tag {
  1: required string  key
  2: required TagType vType
  3: optional string  vStr
  4: optional double  vDouble
  5: optional bool    vBool
  6: optional i64     vLong
  7: optional binary  vBinary
}

# Log is a timed even with an arbitrary set of tags.
struct Log {
  1: required i64       timestamp
  2: required list<Tag> fields
}

enum SpanRefType { CHILD_OF, FOLLOWS_FROM }

# SpanRef describes causal relationship of the current span to another span (e.g. 'child-of')
struct SpanRef {
  1: required SpanRefType refType
  2: required i64         traceIdLow
  3: required i64         traceIdHigh
  4: required i64         spanId
}

# Span represents a named unit of work performed by a service.
struct Span {
  1:  required i64           traceIdLow   # the least significant 64 bits of a traceID
  2:  required i64           traceIdHigh  # the most significant 64 bits of a traceID; 0 when only 64bit IDs are used
  3:  required i64           spanId       # unique span id (only unique within a given trace)
  4:  required i64           parentSpanId # since nearly all spans will have parents spans, CHILD_OF refs do not have to be explicit
  5:  required string        operationName
  6:  optional list<SpanRef> references   # causal references to other spans
  7:  required i32           flags        # a bit field used to propagate sampling decisions. 1 signifies a SAMPLED span, 2 signifies a DEBUG span.
  8:  required i64           startTime
  9:  required i64           duration
  10: optional list<Tag>     tags
  11: optional list<Log>     logs
}

# Process describes the traced process/service that emits spans.
struct Process {
  1: required string    serviceName
  2: optional list<Tag> tags
}

# Batch is a collection of spans reported out of process.
struct Batch {
  1: required Process    process
  2: required list<Span> spans
}

# BatchSubmitResponse is the response on submitting a batch. 
struct BatchSubmitResponse {
    1: required bool ok   # The Collector's client is expected to only log (or emit a counter) when not ok equals false
}

service Collector  {
    list<BatchSubmitResponse> submitBatches(1: list<Batch> batches)
}
