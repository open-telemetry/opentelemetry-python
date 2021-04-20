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


class ResourceAttributes:
    CLOUD_PROVIDER = "cloud.provider"
    """
    Name of the cloud provider.
    """

    CLOUD_ACCOUNT_ID = "cloud.account.id"
    """
    The cloud account ID the resource is assigned to.
    """

    CLOUD_REGION = "cloud.region"
    """
    The geographical region the resource is running. Refer to your provider's docs to see the available regions, for example [AWS regions](https://aws.amazon.com/about-aws/global-infrastructure/regions_az/), [Azure regions](https://azure.microsoft.com/en-us/global-infrastructure/geographies/), or [Google Cloud regions](https://cloud.google.com/about/locations).
    """

    CLOUD_AVAILABILITY_ZONE = "cloud.availability_zone"
    """
    Cloud regions often have multiple, isolated locations known as zones to increase availability. Availability zone represents the zone where the resource is running.
    Note: Availability zones are called "zones" on Google Cloud.
    """

    CLOUD_INFRASTRUCTURE_SERVICE = "cloud.infrastructure_service"
    """
    The cloud infrastructure resource in use.
    Note: The prefix of the service SHOULD match the one specified in `cloud.provider`.
    """

    AWS_ECS_CONTAINER_ARN = "aws.ecs.container.arn"
    """
    The Amazon Resource Name (ARN) of an [ECS container instance](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ECS_instances.html).
    """

    AWS_ECS_CLUSTER_ARN = "aws.ecs.cluster.arn"
    """
    The ARN of an [ECS cluster](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/clusters.html).
    """

    AWS_ECS_LAUNCHTYPE = "aws.ecs.launchtype"
    """
    The [launch type](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/launch_types.html) for an ECS task.
    """

    AWS_ECS_TASK_ARN = "aws.ecs.task.arn"
    """
    The ARN of an [ECS task definition](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html).
    """

    AWS_ECS_TASK_FAMILY = "aws.ecs.task.family"
    """
    The task definition family this task definition is a member of.
    """

    AWS_EKS_CLUSTER_ARN = "aws.eks.cluster.arn"
    """
    The ARN of an EKS cluster.
    """

    AWS_LOG_GROUP_NAMES = "aws.log.group.names"
    """
    The name(s) of the AWS log group(s) an application is writing to.
    Note: Multiple log groups must be supported for cases like multi-container applications, where a single application has sidecar containers, and each write to their own log group.
    """

    AWS_LOG_GROUP_ARNS = "aws.log.group.arns"
    """
    The Amazon Resource Name(s) (ARN) of the AWS log group(s).
    Note: See the [log group ARN format documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/iam-access-control-overview-cwl.html#CWL_ARN_Format).
    """

    AWS_LOG_STREAM_NAMES = "aws.log.stream.names"
    """
    The name(s) of the AWS log stream(s) an application is writing to.
    """

    AWS_LOG_STREAM_ARNS = "aws.log.stream.arns"
    """
    The ARN(s) of the AWS log stream(s).
    Note: See the [log stream ARN format documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/iam-access-control-overview-cwl.html#CWL_ARN_Format). One log group can contain several log streams, so these ARNs necessarily identify both a log group and a log stream.
    """

    CONTAINER_NAME = "container.name"
    """
    Container name.
    """

    CONTAINER_ID = "container.id"
    """
    Container ID. Usually a UUID, as for example used to [identify Docker containers](https://docs.docker.com/engine/reference/run/#container-identification). The UUID might be abbreviated.
    """

    CONTAINER_RUNTIME = "container.runtime"
    """
    The container runtime managing this container.
    """

    CONTAINER_IMAGE_NAME = "container.image.name"
    """
    Name of the image the container was built on.
    """

    CONTAINER_IMAGE_TAG = "container.image.tag"
    """
    Container image tag.
    """

    DEPLOYMENT_ENVIRONMENT = "deployment.environment"
    """
    Name of the [deployment environment](https://en.wikipedia.org/wiki/Deployment_environment) (aka deployment tier).
    """

    FAAS_NAME = "faas.name"
    """
    The name of the function being executed.
    """

    FAAS_ID = "faas.id"
    """
    The unique ID of the function being executed.
    Note: For example, in AWS Lambda this field corresponds to the [ARN](https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html) value, in GCP to the URI of the resource, and in Azure to the [FunctionDirectory](https://github.com/Azure/azure-functions-host/wiki/Retrieving-information-about-the-currently-running-function) field.
    """

    FAAS_VERSION = "faas.version"
    """
    The version string of the function being executed as defined in [Version Attributes](../../resource/semantic_conventions/README.md#version-attributes).
    """

    FAAS_INSTANCE = "faas.instance"
    """
    The execution environment ID as a string.
    """

    FAAS_MAX_MEMORY = "faas.max_memory"
    """
    The amount of memory available to the serverless function in MiB.
    Note: It's recommended to set this attribute since e.g. too little memory can easily stop a Java AWS Lambda function from working correctly. On AWS Lambda, the environment variable `AWS_LAMBDA_FUNCTION_MEMORY_SIZE` provides this information.
    """

    HOST_ID = "host.id"
    """
    Unique host ID. For Cloud, this must be the instance_id assigned by the cloud provider.
    """

    HOST_NAME = "host.name"
    """
    Name of the host. On Unix systems, it may contain what the hostname command returns, or the fully qualified hostname, or another name specified by the user.
    """

    HOST_TYPE = "host.type"
    """
    Type of host. For Cloud, this must be the machine type.
    """

    HOST_ARCH = "host.arch"
    """
    The CPU architecture the host system is running on.
    """

    HOST_IMAGE_NAME = "host.image.name"
    """
    Name of the VM image or OS install the host was instantiated from.
    """

    HOST_IMAGE_ID = "host.image.id"
    """
    VM image ID. For Cloud, this value is from the provider.
    """

    HOST_IMAGE_VERSION = "host.image.version"
    """
    The version string of the VM image as defined in [Version Attributes](README.md#version-attributes).
    """

    K8S_CLUSTER_NAME = "k8s.cluster.name"
    """
    The name of the cluster.
    """

    K8S_NODE_NAME = "k8s.node.name"
    """
    The name of the Node.
    """

    K8S_NODE_UID = "k8s.node.uid"
    """
    The UID of the Node.
    """

    K8S_NAMESPACE_NAME = "k8s.namespace.name"
    """
    The name of the namespace that the pod is running in.
    """

    K8S_POD_UID = "k8s.pod.uid"
    """
    The UID of the Pod.
    """

    K8S_POD_NAME = "k8s.pod.name"
    """
    The name of the Pod.
    """

    K8S_CONTAINER_NAME = "k8s.container.name"
    """
    The name of the Container in a Pod template.
    """

    K8S_REPLICASET_UID = "k8s.replicaset.uid"
    """
    The UID of the ReplicaSet.
    """

    K8S_REPLICASET_NAME = "k8s.replicaset.name"
    """
    The name of the ReplicaSet.
    """

    K8S_DEPLOYMENT_UID = "k8s.deployment.uid"
    """
    The UID of the Deployment.
    """

    K8S_DEPLOYMENT_NAME = "k8s.deployment.name"
    """
    The name of the Deployment.
    """

    K8S_STATEFULSET_UID = "k8s.statefulset.uid"
    """
    The UID of the StatefulSet.
    """

    K8S_STATEFULSET_NAME = "k8s.statefulset.name"
    """
    The name of the StatefulSet.
    """

    K8S_DAEMONSET_UID = "k8s.daemonset.uid"
    """
    The UID of the DaemonSet.
    """

    K8S_DAEMONSET_NAME = "k8s.daemonset.name"
    """
    The name of the DaemonSet.
    """

    K8S_JOB_UID = "k8s.job.uid"
    """
    The UID of the Job.
    """

    K8S_JOB_NAME = "k8s.job.name"
    """
    The name of the Job.
    """

    K8S_CRONJOB_UID = "k8s.cronjob.uid"
    """
    The UID of the CronJob.
    """

    K8S_CRONJOB_NAME = "k8s.cronjob.name"
    """
    The name of the CronJob.
    """

    OS_TYPE = "os.type"
    """
    The operating system type.
    """

    OS_DESCRIPTION = "os.description"
    """
    Human readable (not intended to be parsed) OS version information, like e.g. reported by `ver` or `lsb_release -a` commands.
    """

    PROCESS_PID = "process.pid"
    """
    Process identifier (PID).
    """

    PROCESS_EXECUTABLE_NAME = "process.executable.name"
    """
    The name of the process executable. On Linux based systems, can be set to the `Name` in `proc/[pid]/status`. On Windows, can be set to the base name of `GetProcessImageFileNameW`.
    """

    PROCESS_EXECUTABLE_PATH = "process.executable.path"
    """
    The full path to the process executable. On Linux based systems, can be set to the target of `proc/[pid]/exe`. On Windows, can be set to the result of `GetProcessImageFileNameW`.
    """

    PROCESS_COMMAND = "process.command"
    """
    The command used to launch the process (i.e. the command name). On Linux based systems, can be set to the zeroth string in `proc/[pid]/cmdline`. On Windows, can be set to the first parameter extracted from `GetCommandLineW`.
    """

    PROCESS_COMMAND_LINE = "process.command_line"
    """
    The full command used to launch the process as a single string representing the full command. On Windows, can be set to the result of `GetCommandLineW`. Do not set this if you have to assemble it just for monitoring; use `process.command_args` instead.
    """

    PROCESS_COMMAND_ARGS = "process.command_args"
    """
    All the command arguments (including the command/executable itself) as received by the process. On Linux-based systems (and some other Unixoid systems supporting procfs), can be set according to the list of null-delimited strings extracted from `proc/[pid]/cmdline`. For libc-based executables, this would be the full argv vector passed to `main`.
    """

    PROCESS_OWNER = "process.owner"
    """
    The username of the user that owns the process.
    """

    PROCESS_RUNTIME_NAME = "process.runtime.name"
    """
    The name of the runtime of this process. For compiled native binaries, this SHOULD be the name of the compiler.
    """

    PROCESS_RUNTIME_VERSION = "process.runtime.version"
    """
    The version of the runtime of this process, as returned by the runtime without modification.
    """

    PROCESS_RUNTIME_DESCRIPTION = "process.runtime.description"
    """
    An additional description about the runtime of the process, for example a specific vendor customization of the runtime environment.
    """

    SERVICE_NAME = "service.name"
    """
    Logical name of the service.
    Note: MUST be the same for all instances of horizontally scaled services. If the value was not specified, SDKs MUST fallback to `unknown_service:` concatenated with [`process.executable.name`](process.md#process), e.g. `unknown_service:bash`. If `process.executable.name` is not available, the value MUST be set to `unknown_service`.
    """

    SERVICE_NAMESPACE = "service.namespace"
    """
    A namespace for `service.name`.
    Note: A string value having a meaning that helps to distinguish a group of services, for example the team name that owns a group of services. `service.name` is expected to be unique within the same namespace. If `service.namespace` is not specified in the Resource then `service.name` is expected to be unique for all services that have no explicit namespace defined (so the empty/unspecified namespace is simply one more valid namespace). Zero-length namespace string is assumed equal to unspecified namespace.
    """

    SERVICE_INSTANCE_ID = "service.instance.id"
    """
    The string ID of the service instance.
    Note: MUST be unique for each instance of the same `service.namespace,service.name` pair (in other words `service.namespace,service.name,service.instance.id` triplet MUST be globally unique). The ID helps to distinguish instances of the same service that exist at the same time (e.g. instances of a horizontally scaled service). It is preferable for the ID to be persistent and stay the same for the lifetime of the service instance, however it is acceptable that the ID is ephemeral and changes during important lifetime events for the service (e.g. service restarts). If the service has no inherent unique ID that can be used as the value of this attribute it is recommended to generate a random Version 1 or Version 4 RFC 4122 UUID (services aiming for reproducible UUIDs may also use Version 5, see RFC 4122 for more recommendations).
    """

    SERVICE_VERSION = "service.version"
    """
    The version string of the service API or implementation.
    """

    TELEMETRY_SDK_NAME = "telemetry.sdk.name"
    """
    The name of the telemetry SDK as defined above.
    """

    TELEMETRY_SDK_LANGUAGE = "telemetry.sdk.language"
    """
    The language of the telemetry SDK.
    """

    TELEMETRY_SDK_VERSION = "telemetry.sdk.version"
    """
    The version string of the telemetry SDK.
    """

    TELEMETRY_AUTO_VERSION = "telemetry.auto.version"
    """
    The version string of the auto instrumentation agent, if used.
    """


class CloudProviderValues(Enum):
    AWS = "aws"
    """Amazon Web Services."""

    AZURE = "azure"
    """Microsoft Azure."""

    GCP = "gcp"
    """Google Cloud Platform."""


class CloudInfrastructureServiceValues(Enum):
    AWS_EC2 = "aws_ec2"
    """AWS Elastic Compute Cloud."""

    AWS_ECS = "aws_ecs"
    """AWS Elastic Container Service."""

    AWS_EKS = "aws_eks"
    """AWS Elastic Kubernetes Service."""

    AWS_LAMBDA = "aws_lambda"
    """AWS Lambda."""

    AWS_ELASTICBEANSTALK = "aws_elastic_beanstalk"
    """AWS Elastic Beanstalk."""

    AZURE_VM = "azure_vm"
    """Azure Virtual Machines."""

    AZURE_CONTAINERINSTANCES = "azure_container_instances"
    """Azure Container Instances."""

    AZURE_AKS = "azure_aks"
    """Azure Kubernetes Service."""

    AZURE_FUNCTIONS = "azure_functions"
    """Azure Functions."""

    AZURE_APPSERVICE = "azure_app_service"
    """Azure App Service."""

    GCP_COMPUTEENGINE = "gcp_compute_engine"
    """Google Cloud Compute Engine (GCE)."""

    GCP_CLOUDRUN = "gcp_cloud_run"
    """Google Cloud Run."""

    GCP_KUBERNETESENGINE = "gcp_kubernetes_engine"
    """Google Cloud Kubernetes Engine (GKE)."""

    GCP_CLOUDFUNCTIONS = "gcp_cloud_functions"
    """Google Cloud Functions (GCF)."""

    GCP_APPENGINE = "gcp_app_engine"
    """Google Cloud App Engine (GAE)."""


class AwsEcsLaunchtypeValues(Enum):
    EC2 = "ec2"
    """ec2."""

    FARGATE = "fargate"
    """fargate."""


class HostArchValues(Enum):
    AMD64 = "amd64"
    """AMD64."""

    ARM32 = "arm32"
    """ARM32."""

    ARM64 = "arm64"
    """ARM64."""

    IA64 = "ia64"
    """Itanium."""

    PPC32 = "ppc32"
    """32-bit PowerPC."""

    PPC64 = "ppc64"
    """64-bit PowerPC."""

    X86 = "x86"
    """32-bit x86."""


class OsTypeValues(Enum):
    WINDOWS = "WINDOWS"
    """Microsoft Windows."""

    LINUX = "LINUX"
    """Linux."""

    DARWIN = "DARWIN"
    """Apple Darwin."""

    FREEBSD = "FREEBSD"
    """FreeBSD."""

    NETBSD = "NETBSD"
    """NetBSD."""

    OPENBSD = "OPENBSD"
    """OpenBSD."""

    DRAGONFLYBSD = "DRAGONFLYBSD"
    """DragonFly BSD."""

    HPUX = "HPUX"
    """HP-UX (Hewlett Packard Unix)."""

    AIX = "AIX"
    """AIX (Advanced Interactive eXecutive)."""

    SOLARIS = "SOLARIS"
    """Oracle Solaris."""

    ZOS = "ZOS"
    """IBM z/OS."""


class TelemetrySdkLanguageValues(Enum):
    CPP = "cpp"
    """cpp."""

    DOTNET = "dotnet"
    """dotnet."""

    ERLANG = "erlang"
    """erlang."""

    GO = "go"
    """go."""

    JAVA = "java"
    """java."""

    NODEJS = "nodejs"
    """nodejs."""

    PHP = "php"
    """php."""

    PYTHON = "python"
    """python."""

    RUBY = "ruby"
    """ruby."""

    WEBJS = "webjs"
    """webjs."""
