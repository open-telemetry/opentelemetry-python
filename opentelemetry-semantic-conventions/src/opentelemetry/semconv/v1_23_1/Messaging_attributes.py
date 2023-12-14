
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

# pylint: disable=too-many-lines

from enum import Enum

class MessagingAttributes:

    
    MESSAGING_BATCH_MESSAGE_COUNT = "messaging.batch.message_count"
    
    """
    The number of messages sent, received, or processed in the scope of the batching operation.
    Note: Instrumentations SHOULD NOT set `messaging.batch.message_count` on spans that operate with a single message. When a messaging client library supports both batch and single-message API for the same operation, instrumentations SHOULD use `messaging.batch.message_count` for batching APIs and SHOULD NOT use it for single-message APIs.
    """

    
    MESSAGING_CLIENT_ID = "messaging.client_id"
    
    """
    A unique identifier for the client that consumes or produces a message.
    """

    
    MESSAGING_DESTINATION_ANONYMOUS = "messaging.destination.anonymous"
    
    """
    A boolean that is true if the message destination is anonymous (could be unnamed or have auto-generated name).
    """

    
    MESSAGING_DESTINATION_NAME = "messaging.destination.name"
    
    """
    The message destination name.
    Note: Destination name SHOULD uniquely identify a specific queue, topic or other entity within the broker. If
    the broker doesn't have such notion, the destination name SHOULD uniquely identify the broker.
    """

    
    MESSAGING_DESTINATION_TEMPLATE = "messaging.destination.template"
    
    """
    Low cardinality representation of the messaging destination name.
    Note: Destination names could be constructed from templates. An example would be a destination name involving a user name or product id. Although the destination name in this case is of high cardinality, the underlying template is of low cardinality and can be effectively used for grouping and aggregation.
    """

    
    MESSAGING_DESTINATION_TEMPORARY = "messaging.destination.temporary"
    
    """
    A boolean that is true if the message destination is temporary and might not exist anymore after messages are processed.
    """

    
    MESSAGING_DESTINATION_PUBLISH_ANONYMOUS = "messaging.destination_publish.anonymous"
    
    """
    A boolean that is true if the publish message destination is anonymous (could be unnamed or have auto-generated name).
    """

    
    MESSAGING_DESTINATION_PUBLISH_NAME = "messaging.destination_publish.name"
    
    """
    The name of the original destination the message was published to.
    Note: The name SHOULD uniquely identify a specific queue, topic, or other entity within the broker. If
    the broker doesn't have such notion, the original destination name SHOULD uniquely identify the broker.
    """

    
    MESSAGING_KAFKA_CONSUMER_GROUP = "messaging.kafka.consumer.group"
    
    """
    Name of the Kafka Consumer Group that is handling the message. Only applies to consumers, not producers.
    """

    
    MESSAGING_KAFKA_DESTINATION_PARTITION = "messaging.kafka.destination.partition"
    
    """
    Partition the message is sent to.
    """

    
    MESSAGING_KAFKA_MESSAGE_KEY = "messaging.kafka.message.key"
    
    """
    Message keys in Kafka are used for grouping alike messages to ensure they're processed on the same partition. They differ from `messaging.message.id` in that they're not unique. If the key is `null`, the attribute MUST NOT be set.
    Note: If the key type is not string, it's string representation has to be supplied for the attribute. If the key has no unambiguous, canonical string form, don't include its value.
    """

    
    MESSAGING_KAFKA_MESSAGE_OFFSET = "messaging.kafka.message.offset"
    
    """
    The offset of a record in the corresponding Kafka partition.
    """

    
    MESSAGING_KAFKA_MESSAGE_TOMBSTONE = "messaging.kafka.message.tombstone"
    
    """
    A boolean that is true if the message is a tombstone.
    """

    
    MESSAGING_MESSAGE_BODY_SIZE = "messaging.message.body.size"
    
    """
    The size of the message body in bytes.
    Note: This can refer to both the compressed or uncompressed body size. If both sizes are known, the uncompressed
    body size should be used.
    """

    
    MESSAGING_MESSAGE_CONVERSATION_ID = "messaging.message.conversation_id"
    
    """
    The conversation ID identifying the conversation to which the message belongs, represented as a string. Sometimes called "Correlation ID".
    """

    
    MESSAGING_MESSAGE_ENVELOPE_SIZE = "messaging.message.envelope.size"
    
    """
    The size of the message body and metadata in bytes.
    Note: This can refer to both the compressed or uncompressed size. If both sizes are known, the uncompressed
    size should be used.
    """

    
    MESSAGING_MESSAGE_ID = "messaging.message.id"
    
    """
    A value used by the messaging system as an identifier for the message, represented as a string.
    """

    
    MESSAGING_OPERATION = "messaging.operation"
    
    """
    A string identifying the kind of messaging operation.
    Note: If a custom value is used, it MUST be of low cardinality.
    """

    
    MESSAGING_RABBITMQ_DESTINATION_ROUTING_KEY = "messaging.rabbitmq.destination.routing_key"
    
    """
    RabbitMQ message routing key.
    """

    
    MESSAGING_ROCKETMQ_CLIENT_GROUP = "messaging.rocketmq.client_group"
    
    """
    Name of the RocketMQ producer/consumer group that is handling the message. The client type is identified by the SpanKind.
    """

    
    MESSAGING_ROCKETMQ_CONSUMPTION_MODEL = "messaging.rocketmq.consumption_model"
    
    """
    Model of message consumption. This only applies to consumer spans.
    """

    
    MESSAGING_ROCKETMQ_MESSAGE_DELAY_TIME_LEVEL = "messaging.rocketmq.message.delay_time_level"
    
    """
    The delay time level for delay message, which determines the message delay time.
    """

    
    MESSAGING_ROCKETMQ_MESSAGE_DELIVERY_TIMESTAMP = "messaging.rocketmq.message.delivery_timestamp"
    
    """
    The timestamp in milliseconds that the delay message is expected to be delivered to consumer.
    """

    
    MESSAGING_ROCKETMQ_MESSAGE_GROUP = "messaging.rocketmq.message.group"
    
    """
    It is essential for FIFO message. Messages that belong to the same message group are always processed one by one within the same consumer group.
    """

    
    MESSAGING_ROCKETMQ_MESSAGE_KEYS = "messaging.rocketmq.message.keys"
    
    """
    Key(s) of message, another way to mark message besides message id.
    """

    
    MESSAGING_ROCKETMQ_MESSAGE_TAG = "messaging.rocketmq.message.tag"
    
    """
    The secondary classifier of message besides topic.
    """

    
    MESSAGING_ROCKETMQ_MESSAGE_TYPE = "messaging.rocketmq.message.type"
    
    """
    Type of message.
    """

    
    MESSAGING_ROCKETMQ_NAMESPACE = "messaging.rocketmq.namespace"
    
    """
    Namespace of RocketMQ resources, resources in different namespaces are individual.
    """

    
    MESSAGING_SYSTEM = "messaging.system"
    
    """
    A string identifying the messaging system.
    """
class MessagingOperationValues(Enum):
    PUBLISH = "publish"
    """One or more messages are provided for publishing to an intermediary. If a single message is published, the context of the &#34;Publish&#34; span can be used as the creation context and no &#34;Create&#34; span needs to be created."""

    CREATE = "create"
    """A message is created. &#34;Create&#34; spans always refer to a single message and are used to provide a unique creation context for messages in batch publishing scenarios."""

    RECEIVE = "receive"
    """One or more messages are requested by a consumer. This operation refers to pull-based scenarios, where consumers explicitly call methods of messaging SDKs to receive messages."""

    DELIVER = "deliver"
    """One or more messages are passed to a consumer. This operation refers to push-based scenarios, where consumer register callbacks which get called by messaging SDKs."""


class MessagingRocketmqConsumptionModelValues(Enum):
    CLUSTERING = "clustering"
    """Clustering consumption model."""

    BROADCASTING = "broadcasting"
    """Broadcasting consumption model."""


class MessagingRocketmqMessageTypeValues(Enum):
    NORMAL = "normal"
    """Normal message."""

    FIFO = "fifo"
    """FIFO message."""

    DELAY = "delay"
    """Delay message."""

    TRANSACTION = "transaction"
    """Transaction message."""

