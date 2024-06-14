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

from enum import Enum
from typing import Final

MESSAGING_BATCH_MESSAGE_COUNT: Final = "messaging.batch.message_count"
"""
The number of messages sent, received, or processed in the scope of the batching operation.
Note: Instrumentations SHOULD NOT set `messaging.batch.message_count` on spans that operate with a single message. When a messaging client library supports both batch and single-message API for the same operation, instrumentations SHOULD use `messaging.batch.message_count` for batching APIs and SHOULD NOT use it for single-message APIs.
"""

MESSAGING_CLIENT_ID: Final = "messaging.client_id"
"""
A unique identifier for the client that consumes or produces a message.
"""

MESSAGING_DESTINATION_ANONYMOUS: Final = "messaging.destination.anonymous"
"""
A boolean that is true if the message destination is anonymous (could be unnamed or have auto-generated name).
"""

MESSAGING_DESTINATION_NAME: Final = "messaging.destination.name"
"""
The message destination name.
Note: Destination name SHOULD uniquely identify a specific queue, topic or other entity within the broker. If
    the broker doesn't have such notion, the destination name SHOULD uniquely identify the broker.
"""

MESSAGING_DESTINATION_PARTITION_ID: Final = (
    "messaging.destination.partition.id"
)
"""
The identifier of the partition messages are sent to or received from, unique within the `messaging.destination.name`.
"""

MESSAGING_DESTINATION_TEMPLATE: Final = "messaging.destination.template"
"""
Low cardinality representation of the messaging destination name.
Note: Destination names could be constructed from templates. An example would be a destination name involving a user name or product id. Although the destination name in this case is of high cardinality, the underlying template is of low cardinality and can be effectively used for grouping and aggregation.
"""

MESSAGING_DESTINATION_TEMPORARY: Final = "messaging.destination.temporary"
"""
A boolean that is true if the message destination is temporary and might not exist anymore after messages are processed.
"""

MESSAGING_DESTINATION_PUBLISH_ANONYMOUS: Final = (
    "messaging.destination_publish.anonymous"
)
"""
A boolean that is true if the publish message destination is anonymous (could be unnamed or have auto-generated name).
"""

MESSAGING_DESTINATION_PUBLISH_NAME: Final = (
    "messaging.destination_publish.name"
)
"""
The name of the original destination the message was published to.
Note: The name SHOULD uniquely identify a specific queue, topic, or other entity within the broker. If
    the broker doesn't have such notion, the original destination name SHOULD uniquely identify the broker.
"""

MESSAGING_EVENTHUBS_CONSUMER_GROUP: Final = (
    "messaging.eventhubs.consumer.group"
)
"""
The name of the consumer group the event consumer is associated with.
"""

MESSAGING_EVENTHUBS_MESSAGE_ENQUEUED_TIME: Final = (
    "messaging.eventhubs.message.enqueued_time"
)
"""
The UTC epoch seconds at which the message has been accepted and stored in the entity.
"""

MESSAGING_GCP_PUBSUB_MESSAGE_ORDERING_KEY: Final = (
    "messaging.gcp_pubsub.message.ordering_key"
)
"""
The ordering key for a given message. If the attribute is not present, the message does not have an ordering key.
"""

MESSAGING_KAFKA_CONSUMER_GROUP: Final = "messaging.kafka.consumer.group"
"""
Name of the Kafka Consumer Group that is handling the message. Only applies to consumers, not producers.
"""

MESSAGING_KAFKA_DESTINATION_PARTITION: Final = (
    "messaging.kafka.destination.partition"
)
"""
Deprecated: Replaced by `messaging.destination.partition.id`.
"""

MESSAGING_KAFKA_MESSAGE_KEY: Final = "messaging.kafka.message.key"
"""
Message keys in Kafka are used for grouping alike messages to ensure they're processed on the same partition. They differ from `messaging.message.id` in that they're not unique. If the key is `null`, the attribute MUST NOT be set.
Note: If the key type is not string, it's string representation has to be supplied for the attribute. If the key has no unambiguous, canonical string form, don't include its value.
"""

MESSAGING_KAFKA_MESSAGE_OFFSET: Final = "messaging.kafka.message.offset"
"""
The offset of a record in the corresponding Kafka partition.
"""

MESSAGING_KAFKA_MESSAGE_TOMBSTONE: Final = "messaging.kafka.message.tombstone"
"""
A boolean that is true if the message is a tombstone.
"""

MESSAGING_MESSAGE_BODY_SIZE: Final = "messaging.message.body.size"
"""
The size of the message body in bytes.
Note: This can refer to both the compressed or uncompressed body size. If both sizes are known, the uncompressed
    body size should be used.
"""

MESSAGING_MESSAGE_CONVERSATION_ID: Final = "messaging.message.conversation_id"
"""
The conversation ID identifying the conversation to which the message belongs, represented as a string. Sometimes called "Correlation ID".
"""

MESSAGING_MESSAGE_ENVELOPE_SIZE: Final = "messaging.message.envelope.size"
"""
The size of the message body and metadata in bytes.
Note: This can refer to both the compressed or uncompressed size. If both sizes are known, the uncompressed
    size should be used.
"""

MESSAGING_MESSAGE_ID: Final = "messaging.message.id"
"""
A value used by the messaging system as an identifier for the message, represented as a string.
"""

MESSAGING_OPERATION: Final = "messaging.operation"
"""
A string identifying the kind of messaging operation.
Note: If a custom value is used, it MUST be of low cardinality.
"""

MESSAGING_RABBITMQ_DESTINATION_ROUTING_KEY: Final = (
    "messaging.rabbitmq.destination.routing_key"
)
"""
RabbitMQ message routing key.
"""

MESSAGING_RABBITMQ_MESSAGE_DELIVERY_TAG: Final = (
    "messaging.rabbitmq.message.delivery_tag"
)
"""
RabbitMQ message delivery tag.
"""

MESSAGING_ROCKETMQ_CLIENT_GROUP: Final = "messaging.rocketmq.client_group"
"""
Name of the RocketMQ producer/consumer group that is handling the message. The client type is identified by the SpanKind.
"""

MESSAGING_ROCKETMQ_CONSUMPTION_MODEL: Final = (
    "messaging.rocketmq.consumption_model"
)
"""
Model of message consumption. This only applies to consumer spans.
"""

MESSAGING_ROCKETMQ_MESSAGE_DELAY_TIME_LEVEL: Final = (
    "messaging.rocketmq.message.delay_time_level"
)
"""
The delay time level for delay message, which determines the message delay time.
"""

MESSAGING_ROCKETMQ_MESSAGE_DELIVERY_TIMESTAMP: Final = (
    "messaging.rocketmq.message.delivery_timestamp"
)
"""
The timestamp in milliseconds that the delay message is expected to be delivered to consumer.
"""

MESSAGING_ROCKETMQ_MESSAGE_GROUP: Final = "messaging.rocketmq.message.group"
"""
It is essential for FIFO message. Messages that belong to the same message group are always processed one by one within the same consumer group.
"""

MESSAGING_ROCKETMQ_MESSAGE_KEYS: Final = "messaging.rocketmq.message.keys"
"""
Key(s) of message, another way to mark message besides message id.
"""

MESSAGING_ROCKETMQ_MESSAGE_TAG: Final = "messaging.rocketmq.message.tag"
"""
The secondary classifier of message besides topic.
"""

MESSAGING_ROCKETMQ_MESSAGE_TYPE: Final = "messaging.rocketmq.message.type"
"""
Type of message.
"""

MESSAGING_ROCKETMQ_NAMESPACE: Final = "messaging.rocketmq.namespace"
"""
Namespace of RocketMQ resources, resources in different namespaces are individual.
"""

MESSAGING_SERVICEBUS_DESTINATION_SUBSCRIPTION_NAME: Final = (
    "messaging.servicebus.destination.subscription_name"
)
"""
The name of the subscription in the topic messages are received from.
"""

MESSAGING_SERVICEBUS_DISPOSITION_STATUS: Final = (
    "messaging.servicebus.disposition_status"
)
"""
Describes the [settlement type](https://learn.microsoft.com/azure/service-bus-messaging/message-transfers-locks-settlement#peeklock).
"""

MESSAGING_SERVICEBUS_MESSAGE_DELIVERY_COUNT: Final = (
    "messaging.servicebus.message.delivery_count"
)
"""
Number of deliveries that have been attempted for this message.
"""

MESSAGING_SERVICEBUS_MESSAGE_ENQUEUED_TIME: Final = (
    "messaging.servicebus.message.enqueued_time"
)
"""
The UTC epoch seconds at which the message has been accepted and stored in the entity.
"""

MESSAGING_SYSTEM: Final = "messaging.system"
"""
An identifier for the messaging system being used. See below for a list of well-known identifiers.
"""


class MessagingOperationValues(Enum):
    PUBLISH: Final = "publish"
    """One or more messages are provided for publishing to an intermediary. If a single message is published, the context of the "Publish" span can be used as the creation context and no "Create" span needs to be created."""
    CREATE: Final = "create"
    """A message is created. "Create" spans always refer to a single message and are used to provide a unique creation context for messages in batch publishing scenarios."""
    RECEIVE: Final = "receive"
    """One or more messages are requested by a consumer. This operation refers to pull-based scenarios, where consumers explicitly call methods of messaging SDKs to receive messages."""
    DELIVER: Final = "process"
    """One or more messages are delivered to or processed by a consumer."""
    SETTLE: Final = "settle"
    """One or more messages are settled."""


class MessagingRocketmqConsumptionModelValues(Enum):
    CLUSTERING: Final = "clustering"
    """Clustering consumption model."""
    BROADCASTING: Final = "broadcasting"
    """Broadcasting consumption model."""


class MessagingRocketmqMessageTypeValues(Enum):
    NORMAL: Final = "normal"
    """Normal message."""
    FIFO: Final = "fifo"
    """FIFO message."""
    DELAY: Final = "delay"
    """Delay message."""
    TRANSACTION: Final = "transaction"
    """Transaction message."""


class MessagingServicebusDispositionStatusValues(Enum):
    COMPLETE: Final = "complete"
    """Message is completed."""
    ABANDON: Final = "abandon"
    """Message is abandoned."""
    DEAD_LETTER: Final = "dead_letter"
    """Message is sent to dead letter queue."""
    DEFER: Final = "defer"
    """Message is deferred."""


class MessagingSystemValues(Enum):
    ACTIVEMQ: Final = "activemq"
    """Apache ActiveMQ."""
    AWS_SQS: Final = "aws_sqs"
    """Amazon Simple Queue Service (SQS)."""
    EVENTGRID: Final = "eventgrid"
    """Azure Event Grid."""
    EVENTHUBS: Final = "eventhubs"
    """Azure Event Hubs."""
    SERVICEBUS: Final = "servicebus"
    """Azure Service Bus."""
    GCP_PUBSUB: Final = "gcp_pubsub"
    """Google Cloud Pub/Sub."""
    JMS: Final = "jms"
    """Java Message Service."""
    KAFKA: Final = "kafka"
    """Apache Kafka."""
    RABBITMQ: Final = "rabbitmq"
    """RabbitMQ."""
    ROCKETMQ: Final = "rocketmq"
    """Apache RocketMQ."""
