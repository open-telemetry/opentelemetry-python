# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from enum import Enum
from typing import Final

SERVICE_CRITICALITY: Final = "service.criticality"
"""
The operational criticality of the service.
Note: Application developers are encouraged to set `service.criticality` to express the operational importance of their services. Telemetry consumers MAY use this attribute to optimize telemetry collection or improve user experience.
"""

SERVICE_INSTANCE_COST_CENTER_ID: Final = "service.instance.cost_center.id"
"""
Identifier of the cost center associated with the service instance.
Note: The cost center identifier enables tracking and attribution of service resource costs to organizational units, billing accounts, or teams. It is typically a string identifier such as a billing account ID, cost allocation code, or internal accounting ID.
"""

SERVICE_INSTANCE_COST_CENTER_NAME: Final = "service.instance.cost_center.name"
"""
Name of the cost center associated with the service instance.
Note: A human-readable name of the cost center, department, or organizational unit responsible for the service instance costs.
"""

SERVICE_INSTANCE_ID: Final = "service.instance.id"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.service_attributes.SERVICE_INSTANCE_ID`.
"""

SERVICE_NAME: Final = "service.name"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.service_attributes.SERVICE_NAME`.
"""

SERVICE_NAMESPACE: Final = "service.namespace"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.service_attributes.SERVICE_NAMESPACE`.
"""

SERVICE_PEER_NAME: Final = "service.peer.name"
"""
Deprecated: Use `server.service.name` on the client side or `client.service.name` on the server side.
"""

SERVICE_PEER_NAMESPACE: Final = "service.peer.namespace"
"""
Deprecated: Use `server.service.namespace` on the client side or `client.service.namespace` on the server side.
"""

SERVICE_VERSION: Final = "service.version"
"""
Deprecated in favor of stable :py:const:`opentelemetry.semconv.attributes.service_attributes.SERVICE_VERSION`.
"""


class ServiceCriticalityValues(Enum):
    CRITICAL = "critical"
    """Service is business-critical; downtime directly impacts revenue, user experience, or core functionality."""
    HIGH = "high"
    """Service is important but has degradation tolerance or fallback mechanisms."""
    MEDIUM = "medium"
    """Service provides supplementary functionality; degradation has limited user impact."""
    LOW = "low"
    """Service is non-essential to core operations; used for background tasks or internal tools."""
