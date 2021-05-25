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

"""
This package implements `OpenTelemetry Resources
<https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/resource/sdk.md#resource-sdk>`_:

    *A Resource is an immutable representation of the entity producing
    telemetry. For example, a process producing telemetry that is running in
    a container on Kubernetes has a Pod name, it is in a namespace and
    possibly is part of a Deployment which also has a name. All three of
    these attributes can be included in the Resource.*

Resource objects are created with `Resource.create`, which accepts attributes
(key-values). Resources should NOT be created via constructor, and working with
`Resource` objects should only be done via the Resource API methods. Resource
attributes can also be passed at process invocation in the
:envvar:`OTEL_RESOURCE_ATTRIBUTES` environment variable. You should register
your resource with the  `opentelemetry.sdk.trace.TracerProvider` by passing
them into their constructors. The `Resource` passed to a provider is available
to the exporter, which can send on this information as it sees fit.

.. code-block:: python

    trace.set_tracer_provider(
        TracerProvider(
            resource=Resource.create({
                "service.name": "shoppingcart",
                "service.instance.id": "instance-12",
            }),
        ),
    )
    print(trace.get_tracer_provider().resource.attributes)

    {'telemetry.sdk.language': 'python',
    'telemetry.sdk.name': 'opentelemetry',
    'telemetry.sdk.version': '0.13.dev0',
    'service.name': 'shoppingcart',
    'service.instance.id': 'instance-12'}

Note that the OpenTelemetry project documents certain `"standard attributes"
<https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/resource/semantic_conventions/README.md>`_
that have prescribed semantic meanings, for example ``service.name`` in the
above example.
 """

import abc
import concurrent.futures
import logging
import os
import typing
from json import dumps

import pkg_resources

from opentelemetry.attributes import _filter_attributes
from opentelemetry.sdk.environment_variables import (
    OTEL_RESOURCE_ATTRIBUTES,
    OTEL_SERVICE_NAME,
)
from opentelemetry.semconv.resource import ResourceAttributes

LabelValue = typing.Union[str, bool, int, float]
Attributes = typing.Dict[str, LabelValue]
logger = logging.getLogger(__name__)


CLOUD_PROVIDER = ResourceAttributes.CLOUD_PROVIDER
CLOUD_ACCOUNT_ID = ResourceAttributes.CLOUD_ACCOUNT_ID
CLOUD_REGION = ResourceAttributes.CLOUD_REGION
CLOUD_AVAILABILITY_ZONE = ResourceAttributes.CLOUD_AVAILABILITY_ZONE
CONTAINER_NAME = ResourceAttributes.CONTAINER_NAME
CONTAINER_ID = ResourceAttributes.CONTAINER_ID
CONTAINER_IMAGE_NAME = ResourceAttributes.CONTAINER_IMAGE_NAME
CONTAINER_IMAGE_TAG = ResourceAttributes.CONTAINER_IMAGE_TAG
DEPLOYMENT_ENVIRONMENT = ResourceAttributes.DEPLOYMENT_ENVIRONMENT
FAAS_NAME = ResourceAttributes.FAAS_NAME
FAAS_ID = ResourceAttributes.FAAS_ID
FAAS_VERSION = ResourceAttributes.FAAS_VERSION
FAAS_INSTANCE = ResourceAttributes.FAAS_INSTANCE
HOST_NAME = ResourceAttributes.HOST_NAME
HOST_TYPE = ResourceAttributes.HOST_TYPE
HOST_IMAGE_NAME = ResourceAttributes.HOST_IMAGE_NAME
HOST_IMAGE_ID = ResourceAttributes.HOST_IMAGE_ID
HOST_IMAGE_VERSION = ResourceAttributes.HOST_IMAGE_VERSION
KUBERNETES_CLUSTER_NAME = ResourceAttributes.K8S_CLUSTER_NAME
KUBERNETES_NAMESPACE_NAME = ResourceAttributes.K8S_NAMESPACE_NAME
KUBERNETES_POD_UID = ResourceAttributes.K8S_POD_UID
KUBERNETES_POD_NAME = ResourceAttributes.K8S_POD_NAME
KUBERNETES_CONTAINER_NAME = ResourceAttributes.K8S_CONTAINER_NAME
KUBERNETES_REPLICA_SET_UID = ResourceAttributes.K8S_REPLICASET_UID
KUBERNETES_REPLICA_SET_NAME = ResourceAttributes.K8S_REPLICASET_NAME
KUBERNETES_DEPLOYMENT_UID = ResourceAttributes.K8S_DEPLOYMENT_UID
KUBERNETES_DEPLOYMENT_NAME = ResourceAttributes.K8S_DEPLOYMENT_NAME
KUBERNETES_STATEFUL_SET_UID = ResourceAttributes.K8S_STATEFULSET_UID
KUBERNETES_STATEFUL_SET_NAME = ResourceAttributes.K8S_STATEFULSET_NAME
KUBERNETES_DAEMON_SET_UID = ResourceAttributes.K8S_DAEMONSET_UID
KUBERNETES_DAEMON_SET_NAME = ResourceAttributes.K8S_DAEMONSET_NAME
KUBERNETES_JOB_UID = ResourceAttributes.K8S_JOB_UID
KUBERNETES_JOB_NAME = ResourceAttributes.K8S_JOB_NAME
KUBERNETES_CRON_JOB_UID = ResourceAttributes.K8S_CRONJOB_UID
KUBERNETES_CRON_JOB_NAME = ResourceAttributes.K8S_CRONJOB_NAME
OS_TYPE = ResourceAttributes.OS_TYPE
OS_DESCRIPTION = ResourceAttributes.OS_DESCRIPTION
PROCESS_PID = ResourceAttributes.PROCESS_PID
PROCESS_EXECUTABLE_NAME = ResourceAttributes.PROCESS_EXECUTABLE_NAME
PROCESS_EXECUTABLE_PATH = ResourceAttributes.PROCESS_EXECUTABLE_PATH
PROCESS_COMMAND = ResourceAttributes.PROCESS_COMMAND
PROCESS_COMMAND_LINE = ResourceAttributes.PROCESS_COMMAND_LINE
PROCESS_COMMAND_ARGS = ResourceAttributes.PROCESS_COMMAND_ARGS
PROCESS_OWNER = ResourceAttributes.PROCESS_OWNER
PROCESS_RUNTIME_NAME = ResourceAttributes.PROCESS_RUNTIME_NAME
PROCESS_RUNTIME_VERSION = ResourceAttributes.PROCESS_RUNTIME_VERSION
PROCESS_RUNTIME_DESCRIPTION = ResourceAttributes.PROCESS_RUNTIME_DESCRIPTION
SERVICE_NAME = ResourceAttributes.SERVICE_NAME
SERVICE_NAMESPACE = ResourceAttributes.SERVICE_NAMESPACE
SERVICE_INSTANCE_ID = ResourceAttributes.SERVICE_INSTANCE_ID
SERVICE_VERSION = ResourceAttributes.SERVICE_VERSION
TELEMETRY_SDK_NAME = ResourceAttributes.TELEMETRY_SDK_NAME
TELEMETRY_SDK_VERSION = ResourceAttributes.TELEMETRY_SDK_VERSION
TELEMETRY_AUTO_VERSION = ResourceAttributes.TELEMETRY_AUTO_VERSION
TELEMETRY_SDK_LANGUAGE = ResourceAttributes.TELEMETRY_SDK_LANGUAGE


_OPENTELEMETRY_SDK_VERSION = pkg_resources.get_distribution(
    "opentelemetry-sdk"
).version


class Resource:
    """A Resource is an immutable representation of the entity producing telemetry as Attributes."""

    def __init__(self, attributes: Attributes, schema_url: str):
        _filter_attributes(attributes)
        self._attributes = attributes.copy()
        self._schema_url = schema_url

    @staticmethod
    def create(
        attributes: typing.Optional[Attributes] = None,
        schema_url: typing.Optional[str] = None,
    ) -> "Resource":
        """Creates a new `Resource` from attributes.

        Args:
            attributes: Optional zero or more key-value pairs.
            schema_url: Optional URL pointing to the schema

        Returns:
            The newly-created Resource.
        """
        if not attributes:
            attributes = {}
        if not schema_url:
            schema_url = ""
        resource = _DEFAULT_RESOURCE.merge(
            OTELResourceDetector().detect()
        ).merge(Resource(attributes, schema_url))
        if not resource.attributes.get(SERVICE_NAME, None):
            default_service_name = "unknown_service"
            process_executable_name = resource.attributes.get(
                PROCESS_EXECUTABLE_NAME, None
            )
            if process_executable_name:
                default_service_name += ":" + process_executable_name
            resource = resource.merge(
                Resource({SERVICE_NAME: default_service_name}, schema_url)
            )
        return resource

    @staticmethod
    def get_empty() -> "Resource":
        return _EMPTY_RESOURCE

    @property
    def attributes(self) -> Attributes:
        return self._attributes.copy()

    @property
    def schema_url(self) -> str:
        return self._schema_url

    def merge(self, other: "Resource") -> "Resource":
        """Merges this resource and an updating resource into a new `Resource`.

        If a key exists on both the old and updating resource, the value of the
        updating resource will override the old resource value.

        The new `schema_url` will take an updated value only if the original
        `schema_url` is empty. Attempting to merge two resources with
        different, non-empty values for `schema_url` will result in an error.

        Args:
            other: The other resource to be merged.

        Returns:
            The newly-created Resource.
        """
        merged_attributes = self.attributes
        merged_attributes.update(other.attributes)

        if self.schema_url == "":
            schema_url = other.schema_url
        elif other.schema_url == "":
            schema_url = self.schema_url
        elif self.schema_url == other.schema_url:
            schema_url = other.schema_url
        else:
            schema_url = "merge-conflict"
            logger.error(
                "Failed to merge resources: The Schema URL of the old and updating resources are not empty and are different"
            )

        return Resource(merged_attributes, schema_url)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Resource):
            return False
        return (
            self._attributes == other._attributes
            and self._schema_url == other._schema_url
        )

    def __hash__(self):
        return hash(dumps(self._attributes, sort_keys=True) + self._schema_url)


_EMPTY_RESOURCE = Resource({}, "")
_DEFAULT_RESOURCE = Resource(
    {
        TELEMETRY_SDK_LANGUAGE: "python",
        TELEMETRY_SDK_NAME: "opentelemetry",
        TELEMETRY_SDK_VERSION: _OPENTELEMETRY_SDK_VERSION,
    },
    "",
)


class ResourceDetector(abc.ABC):
    def __init__(self, raise_on_error=False):
        self.raise_on_error = raise_on_error

    @abc.abstractmethod
    def detect(self) -> "Resource":
        raise NotImplementedError()


class OTELResourceDetector(ResourceDetector):
    # pylint: disable=no-self-use
    def detect(self) -> "Resource":
        env_resources_items = os.environ.get(OTEL_RESOURCE_ATTRIBUTES)
        env_resource_map = {}
        if env_resources_items:
            env_resource_map = {
                key.strip(): value.strip()
                for key, value in (
                    item.split("=") for item in env_resources_items.split(",")
                )
            }
        service_name = os.environ.get(OTEL_SERVICE_NAME)
        if service_name:
            env_resource_map[SERVICE_NAME] = service_name
        return Resource(env_resource_map, "")


def get_aggregated_resources(
    detectors: typing.List["ResourceDetector"],
    initial_resource: typing.Optional[Resource] = None,
    timeout=5,
) -> "Resource":
    """Retrieves resources from detectors in the order that they were passed

    :param detectors: List of resources in order of priority
    :param initial_resource: Static resource. This has highest priority
    :param timeout: Number of seconds to wait for each detector to return
    :return:
    """
    final_resource = initial_resource or _EMPTY_RESOURCE
    detectors = [OTELResourceDetector()] + detectors

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(detector.detect) for detector in detectors]
        for detector_ind, future in enumerate(futures):
            detector = detectors[detector_ind]
            try:
                detected_resources = future.result(timeout=timeout)
            # pylint: disable=broad-except
            except Exception as ex:
                if detector.raise_on_error:
                    raise ex
                logger.warning(
                    "Exception %s in detector %s, ignoring", ex, detector
                )
                detected_resources = _EMPTY_RESOURCE
            finally:
                final_resource = final_resource.merge(detected_resources)
    return final_resource
