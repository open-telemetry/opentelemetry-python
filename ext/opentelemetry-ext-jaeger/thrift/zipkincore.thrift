# Copyright 2012 Twitter Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
namespace cpp twitter.zipkin.thrift
namespace java com.twitter.zipkin.thriftjava
#@namespace scala com.twitter.zipkin.thriftscala
namespace rb Zipkin
namespace php Jaeger.Thrift.Agent.Zipkin
namespace netcore Jaeger.Thrift.Agent.Zipkin
namespace lua jaeger.thrift.agent


#************** Annotation.value **************
/**
 * The client sent ("cs") a request to a server. There is only one send per
 * span. For example, if there's a transport error, each attempt can be logged
 * as a WIRE_SEND annotation.
 *
 * If chunking is involved, each chunk could be logged as a separate
 * CLIENT_SEND_FRAGMENT in the same span.
 *
 * Annotation.host is not the server. It is the host which logged the send
 * event, almost always the client. When logging CLIENT_SEND, instrumentation
 * should also log the SERVER_ADDR.
 */
const string CLIENT_SEND = "cs"
/**
 * The client received ("cr") a response from a server. There is only one
 * receive per span. For example, if duplicate responses were received, each
 * can be logged as a WIRE_RECV annotation.
 *
 * If chunking is involved, each chunk could be logged as a separate
 * CLIENT_RECV_FRAGMENT in the same span.
 *
 * Annotation.host is not the server. It is the host which logged the receive
 * event, almost always the client. The actual endpoint of the server is
 * recorded separately as SERVER_ADDR when CLIENT_SEND is logged.
 */
const string CLIENT_RECV = "cr"
/**
 * The server sent ("ss") a response to a client. There is only one response
 * per span. If there's a transport error, each attempt can be logged as a
 * WIRE_SEND annotation.
 *
 * Typically, a trace ends with a server send, so the last timestamp of a trace
 * is often the timestamp of the root span's server send.
 *
 * If chunking is involved, each chunk could be logged as a separate
 * SERVER_SEND_FRAGMENT in the same span.
 *
 * Annotation.host is not the client. It is the host which logged the send
 * event, almost always the server. The actual endpoint of the client is
 * recorded separately as CLIENT_ADDR when SERVER_RECV is logged.
 */
const string SERVER_SEND = "ss"
/**
 * The server received ("sr") a request from a client. There is only one
 * request per span.  For example, if duplicate responses were received, each
 * can be logged as a WIRE_RECV annotation.
 *
 * Typically, a trace starts with a server receive, so the first timestamp of a
 * trace is often the timestamp of the root span's server receive.
 *
 * If chunking is involved, each chunk could be logged as a separate
 * SERVER_RECV_FRAGMENT in the same span.
 *
 * Annotation.host is not the client. It is the host which logged the receive
 * event, almost always the server. When logging SERVER_RECV, instrumentation
 * should also log the CLIENT_ADDR.
 */
const string SERVER_RECV = "sr"
/**
 * Message send ("ms") is a request to send a message to a destination, usually
 * a broker. This may be the only annotation in a messaging span. If WIRE_SEND
 * exists in the same span, it follows this moment and clarifies delays sending
 * the message, such as batching.
 *
 * Unlike RPC annotations like CLIENT_SEND, messaging spans never share a span
 * ID. For example, "ms" should always be the parent of "mr".
 *
 * Annotation.host is not the destination, it is the host which logged the send
 * event: the producer. When annotating MESSAGE_SEND, instrumentation should
 * also tag the MESSAGE_ADDR.
 */
const string MESSAGE_SEND = "ms"
/**
 * A consumer received ("mr") a message from a broker. This may be the only
 * annotation in a messaging span. If WIRE_RECV exists in the same span, it
 * precedes this moment and clarifies any local queuing delay.
 *
 * Unlike RPC annotations like SERVER_RECV, messaging spans never share a span
 * ID. For example, "mr" should always be a child of "ms" unless it is a root
 * span.
 *
 * Annotation.host is not the broker, it is the host which logged the receive
 * event: the consumer.  When annotating MESSAGE_RECV, instrumentation should
 * also tag the MESSAGE_ADDR.
 */
const string MESSAGE_RECV = "mr"
/**
 * Optionally logs an attempt to send a message on the wire. Multiple wire send
 * events could indicate network retries. A lag between client or server send
 * and wire send might indicate queuing or processing delay.
 */
const string WIRE_SEND = "ws"
/**
 * Optionally logs an attempt to receive a message from the wire. Multiple wire
 * receive events could indicate network retries. A lag between wire receive
 * and client or server receive might indicate queuing or processing delay.
 */
const string WIRE_RECV = "wr"
/**
 * Optionally logs progress of a (CLIENT_SEND, WIRE_SEND). For example, this
 * could be one chunk in a chunked request.
 */
const string CLIENT_SEND_FRAGMENT = "csf"
/**
 * Optionally logs progress of a (CLIENT_RECV, WIRE_RECV). For example, this
 * could be one chunk in a chunked response.
 */
const string CLIENT_RECV_FRAGMENT = "crf"
/**
 * Optionally logs progress of a (SERVER_SEND, WIRE_SEND). For example, this
 * could be one chunk in a chunked response.
 */
const string SERVER_SEND_FRAGMENT = "ssf"
/**
 * Optionally logs progress of a (SERVER_RECV, WIRE_RECV). For example, this
 * could be one chunk in a chunked request.
 */
const string SERVER_RECV_FRAGMENT = "srf"

#***** BinaryAnnotation.key ******
/**
 * The value of "lc" is the component or namespace of a local span.
 *
 * BinaryAnnotation.host adds service context needed to support queries.
 *
 * Local Component("lc") supports three key features: flagging, query by
 * service and filtering Span.name by namespace.
 *
 * While structurally the same, local spans are fundamentally different than
 * RPC spans in how they should be interpreted. For example, zipkin v1 tools
 * center on RPC latency and service graphs. Root local-spans are neither
 * indicative of critical path RPC latency, nor have impact on the shape of a
 * service graph. By flagging with "lc", tools can special-case local spans.
 *
 * Zipkin v1 Spans are unqueryable unless they can be indexed by service name.
 * The only path to a service name is by (Binary)?Annotation.host.serviceName.
 * By logging "lc", a local span can be queried even if no other annotations
 * are logged.
 *
 * The value of "lc" is the namespace of Span.name. For example, it might be
 * "finatra2", for a span named "bootstrap". "lc" allows you to resolves
 * conflicts for the same Span.name, for example "finatra/bootstrap" vs
 * "finch/bootstrap". Using local component, you'd search for spans named
 * "bootstrap" where "lc=finch"
 */
const string LOCAL_COMPONENT = "lc"

#***** BinaryAnnotation.key where value = [1] and annotation_type = BOOL ******
/**
 * Indicates a client address ("ca") in a span. Most likely, there's only one.
 * Multiple addresses are possible when a client changes its ip or port within
 * a span.
 */
const string CLIENT_ADDR = "ca"
/**
 * Indicates a server address ("sa") in a span. Most likely, there's only one.
 * Multiple addresses are possible when a client is redirected, or fails to a
 * different server ip or port.
 */
const string SERVER_ADDR = "sa"
/**
 * Indicates the remote address of a messaging span, usually the broker.
 */
const string MESSAGE_ADDR = "ma"

/**
 * Indicates the network context of a service recording an annotation with two
 * exceptions.
 *
 * When a BinaryAnnotation, and key is CLIENT_ADDR or SERVER_ADDR,
 * the endpoint indicates the source or destination of an RPC. This exception
 * allows zipkin to display network context of uninstrumented services, or
 * clients such as web browsers.
 */
struct Endpoint {
  /**
   * IPv4 host address packed into 4 bytes.
   *
   * Ex for the ip 1.2.3.4, it would be (1 << 24) | (2 << 16) | (3 << 8) | 4
   */
  1: i32 ipv4
  /**
   * IPv4 port
   *
   * Note: this is to be treated as an unsigned integer, so watch for negatives.
   *
   * Conventionally, when the port isn't known, port = 0.
   */
  2: i16 port
  /**
   * Service name in lowercase, such as "memcache" or "zipkin-web"
   *
   * Conventionally, when the service name isn't known, service_name = "unknown".
   */
  3: string service_name
  /**
   * IPv6 host address packed into 16 bytes. Ex Inet6Address.getBytes()
   */
  4: optional binary ipv6
}

/**
 * An annotation is similar to a log statement. It includes a host field which
 * allows these events to be attributed properly, and also aggregatable.
 */
struct Annotation {
  /**
   * Microseconds from epoch.
   *
   * This value should use the most precise value possible. For example,
   * gettimeofday or syncing nanoTime against a tick of currentTimeMillis.
   */
  1: i64 timestamp
  2: string value                  // what happened at the timestamp?
  /**
   * Always the host that recorded the event. By specifying the host you allow
   * rollup of all events (such as client requests to a service) by IP address.
   */
  3: optional Endpoint host
  // don't reuse 4: optional i32 OBSOLETE_duration         // how long did the operation take? microseconds
}

enum AnnotationType { BOOL, BYTES, I16, I32, I64, DOUBLE, STRING }

/**
 * Binary annotations are tags applied to a Span to give it context. For
 * example, a binary annotation of "http.uri" could the path to a resource in a
 * RPC call.
 *
 * Binary annotations of type STRING are always queryable, though more a
 * historical implementation detail than a structural concern.
 *
 * Binary annotations can repeat, and vary on the host. Similar to Annotation,
 * the host indicates who logged the event. This allows you to tell the
 * difference between the client and server side of the same key. For example,
 * the key "http.uri" might be different on the client and server side due to
 * rewriting, like "/api/v1/myresource" vs "/myresource. Via the host field,
 * you can see the different points of view, which often help in debugging.
 */
struct BinaryAnnotation {
  1: string key,
  2: binary value,
  3: AnnotationType annotation_type,
  /**
   * The host that recorded tag, which allows you to differentiate between
   * multiple tags with the same key. There are two exceptions to this.
   *
   * When the key is CLIENT_ADDR or SERVER_ADDR, host indicates the source or
   * destination of an RPC. This exception allows zipkin to display network
   * context of uninstrumented services, or clients such as web browsers.
   */
  4: optional Endpoint host
}

/**
 * A trace is a series of spans (often RPC calls) which form a latency tree.
 *
 * The root span is where trace_id = id and parent_id = Nil. The root span is
 * usually the longest interval in the trace, starting with a SERVER_RECV
 * annotation and ending with a SERVER_SEND.
 */
struct Span {
  1: i64 trace_id                  # unique trace id, use for all spans in trace
  /**
   * Span name in lowercase, rpc method for example
   *
   * Conventionally, when the span name isn't known, name = "unknown".
   */
  3: string name,
  4: i64 id,                       # unique span id, only used for this span
  5: optional i64 parent_id,       # parent span id
  6: list<Annotation> annotations, # all annotations/events that occured, sorted by timestamp
  8: list<BinaryAnnotation> binary_annotations # any binary annotations
  9: optional bool debug = 0       # if true, we DEMAND that this span passes all samplers
  /**
   * Microseconds from epoch of the creation of this span.
   *
   * This value should be set directly by instrumentation, using the most
   * precise value possible. For example, gettimeofday or syncing nanoTime
   * against a tick of currentTimeMillis.
   *
   * For compatibilty with instrumentation that precede this field, collectors
   * or span stores can derive this via Annotation.timestamp.
   * For example, SERVER_RECV.timestamp or CLIENT_SEND.timestamp.
   *
   * This field is optional for compatibility with old data: first-party span
   * stores are expected to support this at time of introduction.
   */
  10: optional i64 timestamp,
  /**
   * Measurement of duration in microseconds, used to support queries.
   *
   * This value should be set directly, where possible. Doing so encourages
   * precise measurement decoupled from problems of clocks, such as skew or NTP
   * updates causing time to move backwards.
   *
   * For compatibilty with instrumentation that precede this field, collectors
   * or span stores can derive this by subtracting Annotation.timestamp.
   * For example, SERVER_SEND.timestamp - SERVER_RECV.timestamp.
   *
   * If this field is persisted as unset, zipkin will continue to work, except
   * duration query support will be implementation-specific. Similarly, setting
   * this field non-atomically is implementation-specific.
   *
   * This field is i64 vs i32 to support spans longer than 35 minutes.
   */
  11: optional i64 duration
  /**
   * Optional unique 8-byte additional identifier for a trace. If non zero, this
   * means the trace uses 128 bit traceIds instead of 64 bit.
   */
  12: optional i64 trace_id_high
}

# define TChannel service

struct Response {
    1: required bool ok
}

service ZipkinCollector {
    list<Response> submitZipkinBatch(1: list<Span> spans)
}
