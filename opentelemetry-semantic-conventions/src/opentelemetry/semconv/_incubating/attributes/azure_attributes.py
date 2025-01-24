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

AZURE_CLIENT_ID: Final = "azure.client.id"
"""
The unique identifier of the client instance.
"""

AZURE_COSMOSDB_CONNECTION_MODE: Final = "azure.cosmosdb.connection.mode"
"""
Cosmos client connection mode.
"""

AZURE_COSMOSDB_CONSISTENCY_LEVEL: Final = "azure.cosmosdb.consistency.level"
"""
Account or request [consistency level](https://learn.microsoft.com/azure/cosmos-db/consistency-levels).
"""

AZURE_COSMOSDB_OPERATION_CONTACTED_REGIONS: Final = (
    "azure.cosmosdb.operation.contacted_regions"
)
"""
List of regions contacted during operation in the order that they were contacted. If there is more than one region listed, it indicates that the operation was performed on multiple regions i.e. cross-regional call.
Note: Region name matches the format of `displayName` in [Azure Location API](https://learn.microsoft.com/rest/api/subscription/subscriptions/list-locations?view=rest-subscription-2021-10-01&tabs=HTTP#location).
"""

AZURE_COSMOSDB_OPERATION_REQUEST_CHARGE: Final = (
    "azure.cosmosdb.operation.request_charge"
)
"""
The number of request units consumed by the operation.
"""

AZURE_COSMOSDB_REQUEST_BODY_SIZE: Final = "azure.cosmosdb.request.body.size"
"""
Request payload size in bytes.
"""

AZURE_COSMOSDB_RESPONSE_SUB_STATUS_CODE: Final = (
    "azure.cosmosdb.response.sub_status_code"
)
"""
Cosmos DB sub status code.
"""


class AzureCosmosdbConnectionModeValues(Enum):
    GATEWAY = "gateway"
    """Gateway (HTTP) connection."""
    DIRECT = "direct"
    """Direct connection."""


class AzureCosmosdbConsistencyLevelValues(Enum):
    STRONG = "Strong"
    """strong."""
    BOUNDED_STALENESS = "BoundedStaleness"
    """bounded_staleness."""
    SESSION = "Session"
    """session."""
    EVENTUAL = "Eventual"
    """eventual."""
    CONSISTENT_PREFIX = "ConsistentPrefix"
    """consistent_prefix."""
