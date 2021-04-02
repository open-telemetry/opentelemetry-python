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
your resource with the `opentelemetry.sdk.trace.TracerProvider` and
`opentelemetry.sdk.metrics.MeterProvider` by passing
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

from opentelemetry.sdk.environment_variables import OTEL_RESOURCE_ATTRIBUTES

LabelValue = typing.Union[str, bool, int, float]
Attributes = typing.Dict[str, LabelValue]
logger = logging.getLogger(__name__)


CLOUD_PROVIDER = "cloud.provider"
CLOUD_ACCOUNT_ID = "cloud.account.id"
CLOUD_REGION = "cloud.region"
CLOUD_ZONE = "cloud.zone"
CONTAINER_NAME = "container.name"
CONTAINER_ID = "container.id"
CONTAINER_IMAGE_NAME = "container.image.name"
CONTAINER_IMAGE_TAG = "container.image.tag"
DEPLOYMENT_ENVIRONMENT = "deployment.environment"
FAAS_NAME = "faas.name"
FAAS_ID = "faas.id"
FAAS_VERSION = "faas.version"
FAAS_INSTANCE = "faas.instance"
HOST_NAME = "host.name"
HOST_TYPE = "host.type"
HOST_IMAGE_NAME = "host.image.name"
HOST_IMAGE_ID = "host.image.id"
HOST_IMAGE_VERSION = "host.image.version"
KUBERNETES_CLUSTER_NAME = "k8s.cluster.name"
KUBERNETES_NAMESPACE_NAME = "k8s.namespace.name"
KUBERNETES_POD_UID = "k8s.pod.uid"
KUBERNETES_POD_NAME = "k8s.pod.name"
KUBERNETES_CONTAINER_NAME = "k8s.container.name"
KUBERNETES_REPLICA_SET_UID = "k8s.replicaset.uid"
KUBERNETES_REPLICA_SET_NAME = "k8s.replicaset.name"
KUBERNETES_DEPLOYMENT_UID = "k8s.deployment.uid"
KUBERNETES_DEPLOYMENT_NAME = "k8s.deployment.name"
KUBERNETES_STATEFUL_SET_UID = "k8s.statefulset.uid"
KUBERNETES_STATEFUL_SET_NAME = "k8s.statefulset.name"
KUBERNETES_DAEMON_SET_UID = "k8s.daemonset.uid"
KUBERNETES_DAEMON_SET_NAME = "k8s.daemonset.name"
KUBERNETES_JOB_UID = "k8s.job.uid"
KUBERNETES_JOB_NAME = "k8s.job.name"
KUBERNETES_CRON_JOB_UID = "k8s.cronjob.uid"
KUBERNETES_CRON_JOB_NAME = "k8s.cronjob.name"
OS_TYPE = "os.type"
OS_DESCRIPTION = "os.description"
PROCESS_PID = "process.pid"
PROCESS_EXECUTABLE_NAME = "process.executable.name"
PROCESS_EXECUTABLE_PATH = "process.executable.path"
PROCESS_COMMAND = "process.command"
PROCESS_COMMAND_LINE = "process.command_line"
PROCESS_COMMAND_ARGS = "process.command_args"
PROCESS_OWNER = "process.owner"
PROCESS_RUNTIME_NAME = "process.runtime.name"
PROCESS_RUNTIME_VERSION = "process.runtime.version"
PROCESS_RUNTIME_DESCRIPTION = "process.runtime.description"
SERVICE_NAME = "service.name"
SERVICE_NAMESPACE = "service.namespace"
SERVICE_INSTANCE_ID = "service.instance.id"
SERVICE_VERSION = "service.version"
TELEMETRY_SDK_NAME = "telemetry.sdk.name"
TELEMETRY_SDK_VERSION = "telemetry.sdk.version"
TELEMETRY_AUTO_VERSION = "telemetry.auto.version"
TELEMETRY_SDK_LANGUAGE = "telemetry.sdk.language"


_OPENTELEMETRY_SDK_VERSION = pkg_resources.get_distribution(
    "opentelemetry-sdk"
).version


class Resource:
    """A Resource is an immutable representation of the entity producing telemetry as Attributes."""

    def __init__(self, attributes: Attributes):
        self._attributes = attributes.copy()

    @staticmethod
    def create(attributes: typing.Optional[Attributes] = None) -> "Resource":
        """Creates a new `Resource` from attributes.

        Args:
            attributes: Optional zero or more key-value pairs.

        Returns:
            The newly-created Resource.
        """
        if not attributes:
            attributes = {}
        resource = _DEFAULT_RESOURCE.merge(
            OTELResourceDetector().detect()
        ).merge(Resource(attributes))
        if not resource.attributes.get(SERVICE_NAME, None):
            default_service_name = "unknown_service"
            process_executable_name = resource.attributes.get(
                PROCESS_EXECUTABLE_NAME, None
            )
            if process_executable_name:
                default_service_name += ":" + process_executable_name
            resource = resource.merge(
                Resource({SERVICE_NAME: default_service_name})
            )
        return resource

    @staticmethod
    def get_empty() -> "Resource":
        return _EMPTY_RESOURCE

    @property
    def attributes(self) -> Attributes:
        return self._attributes.copy()

    def merge(self, other: "Resource") -> "Resource":
        """Merges this resource and an updating resource into a new `Resource`.

        If a key exists on both the old and updating resource, the value of the
        updating resource will override the old resource value.

        Args:
            other: The other resource to be merged.

        Returns:
            The newly-created Resource.
        """
        merged_attributes = self.attributes
        merged_attributes.update(other.attributes)
        return Resource(merged_attributes)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Resource):
            return False
        return self._attributes == other._attributes

    def __hash__(self):
        return hash(dumps(self._attributes, sort_keys=True))


_EMPTY_RESOURCE = Resource({})
_DEFAULT_RESOURCE = Resource(
    {
        TELEMETRY_SDK_LANGUAGE: "python",
        TELEMETRY_SDK_NAME: "opentelemetry",
        TELEMETRY_SDK_VERSION: _OPENTELEMETRY_SDK_VERSION,
    }
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
        return Resource(env_resource_map)


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
