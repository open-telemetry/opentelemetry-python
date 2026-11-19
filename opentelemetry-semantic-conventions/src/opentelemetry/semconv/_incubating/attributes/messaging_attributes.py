# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from enum import Enum
from typing import Final

from typing_extensions import deprecated

MESSAGING_BATCH_MESSAGE_COUNT: Final = "messaging.batch.message_count"
"""
The number of messages sent, received, or processed in the scope of the batching operation.
Note: Instrumentations SHOULD NOT set `messaging.batch.message_count` on spans that operate with a single message. When a messaging client library supports both batch and single-message API for the same operation, instrumentations SHOULD use `messaging.batch.message_count` for batching APIs and SHOULD NOT use it for single-message APIs.
"""

MESSAGING_CLIENT_ID: Final = "messaging.client.id"
"""
A unique identifier for the client that consumes or produces a message.
"""

MESSAGING_CONSUMER_GROUP_NAME: Final = "messaging.consumer.group.name"
"""
The name of the consumer group with which a consumer is associated.
Note: Semantic conventions for individual messaging systems SHOULD document whether `messaging.consumer.group.name` is applicable and what it means in the context of that system.
"""

MESSAGING_DESTINATION_ANONYMOUS: Final = "messaging.destination.anonymous"
"""
A boolean that is true if the message destination is anonymous (could be unnamed or have auto-generated name).
"""

MESSAGING_DESTINATION_NAME: Final = "messaging.destination.name"
"""
The message destination name.
Note: SHOULD uniquely identify a specific queue, topic or other entity within the broker. If
the broker doesn't have such notion, it SHOULD uniquely identify the broker.
"""

MESSAGING_DESTINATION_PARTITION_ID: Final = "messaging.destination.partition.id"
"""
The identifier of the partition messages are sent to or received from, unique within the `messaging.destination.name`.
"""

MESSAGING_DESTINATION_SUBSCRIPTION_NAME: Final = "messaging.destination.subscription.name"
"""
The name of the destination subscription from which a message is consumed.
Note: Semantic conventions for individual messaging systems SHOULD document whether `messaging.destination.subscription.name` is applicable and what it means in the context of that system.
"""

MESSAGING_DESTINATION_TEMPLATE: Final = "messaging.destination.template"
"""
Low cardinality representation of the messaging destination name.
Note: Destination names could be constructed from templates. An example would be a destination name involving a username or product ID. Although the destination name in this case is of high cardinality, the underlying template is of low cardinality and can be effectively used for grouping and aggregation.
"""

MESSAGING_DESTINATION_TEMPORARY: Final = "messaging.destination.temporary"
"""
A boolean that is true if the message destination is temporary and might not exist anymore after messages are processed.
"""

MESSAGING_DESTINATION_PUBLISH_ANONYMOUS: Final = "messaging.destination_publish.anonymous"
"""
Deprecated: Removed. No replacement at this time.
"""

MESSAGING_DESTINATION_PUBLISH_NAME: Final = "messaging.destination_publish.name"
"""
Deprecated: Removed. No replacement at this time.
"""

MESSAGING_EVENTHUBS_CONSUMER_GROUP: Final = "messaging.eventhubs.consumer.group"
"""
Deprecated: Replaced by `messaging.consumer.group.name`.
"""

MESSAGING_EVENTHUBS_MESSAGE_ENQUEUED_TIME: Final = "messaging.eventhubs.message.enqueued_time"
"""
Deprecated: Replaced by `azure.eventhubs.message.enqueued_time`.
"""

MESSAGING_GCP_PUBSUB_MESSAGE_ACK_DEADLINE: Final = "messaging.gcp_pubsub.message.ack_deadline"
"""
Deprecated: Replaced by `gcp.pubsub.message.ack_deadline`.
"""

MESSAGING_GCP_PUBSUB_MESSAGE_ACK_ID: Final = "messaging.gcp_pubsub.message.ack_id"
"""
Deprecated: Replaced by `gcp.pubsub.message.ack_id`.
"""

MESSAGING_GCP_PUBSUB_MESSAGE_DELIVERY_ATTEMPT: Final = "messaging.gcp_pubsub.message.delivery_attempt"
"""
Deprecated: Replaced by `gcp.pubsub.message.delivery_attempt`.
"""

MESSAGING_GCP_PUBSUB_MESSAGE_ORDERING_KEY: Final = "messaging.gcp_pubsub.message.ordering_key"
"""
Deprecated: Replaced by `gcp.pubsub.message.ordering_key`.
"""

MESSAGING_KAFKA_CLUSTER_ID: Final = "messaging.kafka.cluster.id"
"""
Deprecated: Replaced by `kafka.cluster.id`.
"""

MESSAGING_KAFKA_CONSUMER_GROUP: Final = "messaging.kafka.consumer.group"
"""
Deprecated: Replaced by `messaging.consumer.group.name`.
"""

MESSAGING_KAFKA_DESTINATION_PARTITION: Final = "messaging.kafka.destination.partition"
"""
Deprecated: Record string representation of the partition ID in `messaging.destination.partition.id` attribute.
"""

MESSAGING_KAFKA_MESSAGE_KEY: Final = "messaging.kafka.message.key"
"""
Deprecated: Replaced by `kafka.message.key`.
"""

MESSAGING_KAFKA_MESSAGE_OFFSET: Final = "messaging.kafka.message.offset"
"""
Deprecated: Replaced by `kafka.offset`.
"""

MESSAGING_KAFKA_MESSAGE_TOMBSTONE: Final = "messaging.kafka.message.tombstone"
"""
Deprecated: Replaced by `kafka.message.tombstone`.
"""

MESSAGING_KAFKA_OFFSET: Final = "messaging.kafka.offset"
"""
Deprecated: Replaced by `kafka.offset`.
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
Deprecated: Replaced by `messaging.operation.type`.
"""

MESSAGING_OPERATION_NAME: Final = "messaging.operation.name"
"""
The system-specific name of the messaging operation.
"""

MESSAGING_OPERATION_TYPE: Final = "messaging.operation.type"
"""
A string identifying the type of the messaging operation.
Note: If a custom value is used, it MUST be of low cardinality.
"""

MESSAGING_RABBITMQ_DESTINATION_ROUTING_KEY: Final = "messaging.rabbitmq.destination.routing_key"
"""
Deprecated: Replaced by `rabbitmq.destination.routing_key`.
"""

MESSAGING_RABBITMQ_MESSAGE_DELIVERY_TAG: Final = "messaging.rabbitmq.message.delivery_tag"
"""
Deprecated: Replaced by `rabbitmq.message.delivery_tag`.
"""

MESSAGING_ROCKETMQ_CLIENT_GROUP: Final = "messaging.rocketmq.client_group"
"""
Deprecated: Replaced by `messaging.consumer.group.name` on the consumer spans. No replacement for producer spans.
"""

MESSAGING_ROCKETMQ_CONSUMPTION_MODEL: Final = "messaging.rocketmq.consumption_model"
"""
Deprecated: Replaced by `rocketmq.consumption_model`.
"""

MESSAGING_ROCKETMQ_MESSAGE_DELAY_TIME_LEVEL: Final = "messaging.rocketmq.message.delay_time_level"
"""
Deprecated: Replaced by `rocketmq.message.delay_time_level`.
"""

MESSAGING_ROCKETMQ_MESSAGE_DELIVERY_TIMESTAMP: Final = "messaging.rocketmq.message.delivery_timestamp"
"""
Deprecated: Replaced by `rocketmq.message.delivery_timestamp`.
"""

MESSAGING_ROCKETMQ_MESSAGE_GROUP: Final = "messaging.rocketmq.message.group"
"""
Deprecated: Replaced by `rocketmq.message.group`.
"""

MESSAGING_ROCKETMQ_MESSAGE_KEYS: Final = "messaging.rocketmq.message.keys"
"""
Deprecated: Replaced by `rocketmq.message.keys`.
"""

MESSAGING_ROCKETMQ_MESSAGE_TAG: Final = "messaging.rocketmq.message.tag"
"""
Deprecated: Replaced by `rocketmq.message.tag`.
"""

MESSAGING_ROCKETMQ_MESSAGE_TYPE: Final = "messaging.rocketmq.message.type"
"""
Deprecated: Replaced by `rocketmq.message.type`.
"""

MESSAGING_ROCKETMQ_NAMESPACE: Final = "messaging.rocketmq.namespace"
"""
Deprecated: Replaced by `rocketmq.namespace`.
"""

MESSAGING_SERVICEBUS_DESTINATION_SUBSCRIPTION_NAME: Final = "messaging.servicebus.destination.subscription_name"
"""
Deprecated: Replaced by `messaging.destination.subscription.name`.
"""

MESSAGING_SERVICEBUS_DISPOSITION_STATUS: Final = "messaging.servicebus.disposition_status"
"""
Deprecated: Replaced by `azure.servicebus.disposition_status`.
"""

MESSAGING_SERVICEBUS_MESSAGE_DELIVERY_COUNT: Final = "messaging.servicebus.message.delivery_count"
"""
Deprecated: Replaced by `azure.servicebus.message.delivery_count`.
"""

MESSAGING_SERVICEBUS_MESSAGE_ENQUEUED_TIME: Final = "messaging.servicebus.message.enqueued_time"
"""
Deprecated: Replaced by `azure.servicebus.message.enqueued_time`.
"""

MESSAGING_SYSTEM: Final = "messaging.system"
"""
Deprecated: Replaced by `messaging.system.name`.
"""

MESSAGING_SYSTEM_NAME: Final = "messaging.system.name"
"""
The messaging system as identified by the client instrumentation.
Note: The actual messaging system may differ from the one known by the client. For example, when using Kafka client libraries to communicate with Azure Event Hubs, the `messaging.system.name` is set to `kafka` based on the instrumentation's best knowledge.
"""


class MessagingOperationTypeValues(Enum):
    CREATE = "create"
    """A message is created. "Create" spans always refer to a single message and are used to provide a unique creation context for messages in batch sending scenarios."""
    SEND = "send"
    """One or more messages are provided for sending to an intermediary. If a single message is sent, the context of the "Send" span can be used as the creation context and no "Create" span needs to be created."""
    RECEIVE = "receive"
    """One or more messages are requested by a consumer. This operation refers to pull-based scenarios, where consumers explicitly call methods of messaging SDKs to receive messages."""
    PROCESS = "process"
    """One or more messages are processed by a consumer."""
    SETTLE = "settle"
    """One or more messages are settled."""
    DELIVER = "deliver"
    """Deprecated: Replaced by `process`."""
    PUBLISH = "publish"
    """Deprecated: Replaced by `send`."""


@deprecated(
    "The attribute messaging.rocketmq.consumption_model is deprecated - Replaced by `rocketmq.consumption_model`"
)
class MessagingRocketmqConsumptionModelValues(Enum):
    CLUSTERING = "clustering"
    """Clustering consumption model."""
    BROADCASTING = "broadcasting"
    """Broadcasting consumption model."""


@deprecated("The attribute messaging.rocketmq.message.type is deprecated - Replaced by `rocketmq.message.type`")
class MessagingRocketmqMessageTypeValues(Enum):
    NORMAL = "normal"
    """Normal message."""
    FIFO = "fifo"
    """FIFO message."""
    DELAY = "delay"
    """Delay message."""
    TRANSACTION = "transaction"
    """Transaction message."""


@deprecated(
    "The attribute messaging.servicebus.disposition_status is deprecated - Replaced by `azure.servicebus.disposition_status`"
)
class MessagingServicebusDispositionStatusValues(Enum):
    COMPLETE = "complete"
    """Message is completed."""
    ABANDON = "abandon"
    """Message is abandoned."""
    DEAD_LETTER = "dead_letter"
    """Message is sent to dead letter queue."""
    DEFER = "defer"
    """Message is deferred."""


@deprecated("The attribute messaging.system is deprecated - Replaced by `messaging.system.name`")
class MessagingSystemValues(Enum):
    ACTIVEMQ = "activemq"
    """Apache ActiveMQ."""
    AWS_SNS = "aws.sns"
    """Amazon Simple Notification Service (SNS)."""
    AWS_SQS = "aws_sqs"
    """Amazon Simple Queue Service (SQS)."""
    EVENTGRID = "eventgrid"
    """Azure Event Grid."""
    EVENTHUBS = "eventhubs"
    """Azure Event Hubs."""
    SERVICEBUS = "servicebus"
    """Azure Service Bus."""
    GCP_PUBSUB = "gcp_pubsub"
    """Google Cloud Pub/Sub."""
    JMS = "jms"
    """Java Message Service."""
    KAFKA = "kafka"
    """Apache Kafka."""
    RABBITMQ = "rabbitmq"
    """RabbitMQ."""
    ROCKETMQ = "rocketmq"
    """Apache RocketMQ."""
    PULSAR = "pulsar"
    """Apache Pulsar."""


class MessagingSystemNameValues(Enum):
    ACTIVEMQ = "activemq"
    """Apache ActiveMQ."""
    AWS_SNS = "aws.sns"
    """Amazon Simple Notification Service (SNS)."""
    AWS_SQS = "aws.sqs"
    """Amazon Simple Queue Service (SQS)."""
    AZURE_EVENTGRID = "azure.eventgrid"
    """Azure Event Grid."""
    AZURE_EVENTHUBS = "azure.eventhubs"
    """Azure Event Hubs."""
    AZURE_SERVICEBUS = "azure.servicebus"
    """Azure Service Bus."""
    GCP_PUBSUB = "gcp.pubsub"
    """Google Cloud Pub/Sub."""
    JMS = "jms"
    """Java Message Service."""
    KAFKA = "kafka"
    """Apache Kafka."""
    RABBITMQ = "rabbitmq"
    """RabbitMQ."""
    ROCKETMQ = "rocketmq"
    """Apache RocketMQ."""
    PULSAR = "pulsar"
    """Apache Pulsar."""
