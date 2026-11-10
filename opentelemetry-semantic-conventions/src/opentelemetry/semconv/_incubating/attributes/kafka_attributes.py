# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from typing import Final

KAFKA_CLUSTER_ID: Final = "kafka.cluster.id"
"""
The Kafka cluster ID, obtained from the broker metadata exposed through the Kafka client (or AdminClient) API.
Note: The cluster ID is a unique identifier reported by the Kafka broker. It identifies the cluster independently of the individual brokers the client is configured to connect to, and remains stable even if broker hostnames, IP addresses, or ports change.
"""

KAFKA_MESSAGE_KEY: Final = "kafka.message.key"
"""
Message keys in Kafka are used for grouping alike messages to ensure they're processed on the same partition. They differ from `messaging.message.id` in that they're not unique. If the key is `null`, the attribute MUST NOT be set.
Note: If the key type is not string, its string representation has to be supplied for the attribute. If the key has no unambiguous, canonical string form, don't include its value.
"""

KAFKA_MESSAGE_TOMBSTONE: Final = "kafka.message.tombstone"
"""
A boolean that is true if the message is a tombstone.
"""

KAFKA_OFFSET: Final = "kafka.offset"
"""
The offset of a record in the corresponding Kafka partition.
"""
