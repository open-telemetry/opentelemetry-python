# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from enum import Enum
from typing import Final

ROCKETMQ_CONSUMPTION_MODEL: Final = "rocketmq.consumption_model"
"""
Model of message consumption. This only applies to consumer spans.
"""

ROCKETMQ_MESSAGE_DELAY_TIME_LEVEL: Final = "rocketmq.message.delay_time_level"
"""
The delay time level for delay message, which determines the message delay time.
"""

ROCKETMQ_MESSAGE_DELIVERY_TIMESTAMP: Final = "rocketmq.message.delivery_timestamp"
"""
The timestamp in milliseconds that the delay message is expected to be delivered to consumer.
"""

ROCKETMQ_MESSAGE_GROUP: Final = "rocketmq.message.group"
"""
It is essential for FIFO message. Messages that belong to the same message group are always processed one by one within the same consumer group.
"""

ROCKETMQ_MESSAGE_KEYS: Final = "rocketmq.message.keys"
"""
Key(s) of message, another way to mark message besides message ID.
"""

ROCKETMQ_MESSAGE_TAG: Final = "rocketmq.message.tag"
"""
The secondary classifier of message besides topic.
"""

ROCKETMQ_MESSAGE_TYPE: Final = "rocketmq.message.type"
"""
Type of message.
"""

ROCKETMQ_NAMESPACE: Final = "rocketmq.namespace"
"""
Namespace of RocketMQ resources, resources in different namespaces are individual.
"""


class RocketmqConsumptionModelValues(Enum):
    CLUSTERING = "clustering"
    """Clustering consumption model."""
    BROADCASTING = "broadcasting"
    """Broadcasting consumption model."""


class RocketmqMessageTypeValues(Enum):
    NORMAL = "normal"
    """Normal message."""
    FIFO = "fifo"
    """FIFO message."""
    DELAY = "delay"
    """Delay message."""
    TRANSACTION = "transaction"
    """Transaction message."""
