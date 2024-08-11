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

GRAPHQL_DOCUMENT: Final = "graphql.document"
"""
The GraphQL document being executed.
Note: The value may be sanitized to exclude sensitive information.
"""

GRAPHQL_OPERATION_NAME: Final = "graphql.operation.name"
"""
The name of the operation being executed.
"""

GRAPHQL_OPERATION_TYPE: Final = "graphql.operation.type"
"""
The type of the operation being executed.
"""


class GraphqlOperationTypeValues(Enum):
    QUERY: Final = "query"
    """GraphQL query."""
    MUTATION: Final = "mutation"
    """GraphQL mutation."""
    SUBSCRIPTION: Final = "subscription"
    """GraphQL subscription."""
