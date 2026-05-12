# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from enum import Enum
from typing import Final

DEPLOYMENT_ENVIRONMENT: Final = "deployment.environment"
"""
Deprecated: Replaced by `deployment.environment.name`.
"""

DEPLOYMENT_ENVIRONMENT_NAME: Final = "deployment.environment.name"
"""
Name of the [deployment environment](https://wikipedia.org/wiki/Deployment_environment) (aka deployment tier).
Note: `deployment.environment.name` does not affect the uniqueness constraints defined through
the `service.namespace`, `service.name` and `service.instance.id` resource attributes.
This implies that resources carrying the following attribute combinations MUST be
considered to be identifying the same service:

- `service.name=frontend`, `deployment.environment.name=production`
- `service.name=frontend`, `deployment.environment.name=staging`.
"""

DEPLOYMENT_ID: Final = "deployment.id"
"""
The id of the deployment.
"""

DEPLOYMENT_NAME: Final = "deployment.name"
"""
The name of the deployment.
"""

DEPLOYMENT_STATUS: Final = "deployment.status"
"""
The status of the deployment.
"""


class DeploymentStatusValues(Enum):
    FAILED = "failed"
    """failed."""
    SUCCEEDED = "succeeded"
    """succeeded."""
