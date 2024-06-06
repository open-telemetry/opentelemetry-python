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

CLOUD_ACCOUNT_ID = "cloud.account.id"
"""
The cloud account ID the resource is assigned to.
"""

CLOUD_AVAILABILITYZONE = "cloud.availability_zone"
"""
Cloud regions often have multiple, isolated locations known as zones to increase availability. Availability zone represents the zone where the resource is running.
Note: Availability zones are called "zones" on Alibaba Cloud and Google Cloud.
"""

CLOUD_PLATFORM = "cloud.platform"
"""
The cloud platform in use.
Note: The prefix of the service SHOULD match the one specified in `cloud.provider`.
"""

CLOUD_PROVIDER = "cloud.provider"
"""
Name of the cloud provider.
"""

CLOUD_REGION = "cloud.region"
"""
The geographical region the resource is running.
Note: Refer to your provider's docs to see the available regions, for example [Alibaba Cloud regions](https://www.alibabacloud.com/help/doc-detail/40654.htm), [AWS regions](https://aws.amazon.com/about-aws/global-infrastructure/regions_az/), [Azure regions](https://azure.microsoft.com/global-infrastructure/geographies/), [Google Cloud regions](https://cloud.google.com/about/locations), or [Tencent Cloud regions](https://www.tencentcloud.com/document/product/213/6091).
"""

CLOUD_RESOURCEID = "cloud.resource_id"
"""
Cloud provider-specific native identifier of the monitored cloud resource (e.g. an [ARN](https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html) on AWS, a [fully qualified resource ID](https://learn.microsoft.com/rest/api/resources/resources/get-by-id) on Azure, a [full resource name](https://cloud.google.com/apis/design/resource_names#full_resource_name) on GCP).
Note: On some cloud providers, it may not be possible to determine the full ID at startup,
    so it may be necessary to set `cloud.resource_id` as a span attribute instead.

    The exact value to use for `cloud.resource_id` depends on the cloud provider.
    The following well-known definitions MUST be used if you set this attribute and they apply:

    * **AWS Lambda:** The function [ARN](https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html).
      Take care not to use the "invoked ARN" directly but replace any
      [alias suffix](https://docs.aws.amazon.com/lambda/latest/dg/configuration-aliases.html)
      with the resolved function version, as the same runtime instance may be invokable with
      multiple different aliases.
    * **GCP:** The [URI of the resource](https://cloud.google.com/iam/docs/full-resource-names)
    * **Azure:** The [Fully Qualified Resource ID](https://docs.microsoft.com/rest/api/resources/resources/get-by-id) of the invoked function,
      *not* the function app, having the form
      `/subscriptions/<SUBSCIPTION_GUID>/resourceGroups/<RG>/providers/Microsoft.Web/sites/<FUNCAPP>/functions/<FUNC>`.
      This means that a span attribute MUST be used, as an Azure function app can host multiple functions that would usually share
      a TracerProvider.
"""


class CloudPlatformValues(Enum):
    ALIBABACLOUDECS = "alibaba_cloud_ecs"
    """Alibaba Cloud Elastic Compute Service."""
    ALIBABACLOUDFC = "alibaba_cloud_fc"
    """Alibaba Cloud Function Compute."""
    ALIBABACLOUDOPENSHIFT = "alibaba_cloud_openshift"
    """Red Hat OpenShift on Alibaba Cloud."""
    AWSEC2 = "aws_ec2"
    """AWS Elastic Compute Cloud."""
    AWSECS = "aws_ecs"
    """AWS Elastic Container Service."""
    AWSEKS = "aws_eks"
    """AWS Elastic Kubernetes Service."""
    AWSLAMBDA = "aws_lambda"
    """AWS Lambda."""
    AWSELASTICBEANSTALK = "aws_elastic_beanstalk"
    """AWS Elastic Beanstalk."""
    AWSAPPRUNNER = "aws_app_runner"
    """AWS App Runner."""
    AWSOPENSHIFT = "aws_openshift"
    """Red Hat OpenShift on AWS (ROSA)."""
    AZUREVM = "azure_vm"
    """Azure Virtual Machines."""
    AZURECONTAINERAPPS = "azure_container_apps"
    """Azure Container Apps."""
    AZURECONTAINERINSTANCES = "azure_container_instances"
    """Azure Container Instances."""
    AZUREAKS = "azure_aks"
    """Azure Kubernetes Service."""
    AZUREFUNCTIONS = "azure_functions"
    """Azure Functions."""
    AZUREAPPSERVICE = "azure_app_service"
    """Azure App Service."""
    AZUREOPENSHIFT = "azure_openshift"
    """Azure Red Hat OpenShift."""
    GCPBAREMETALSOLUTION = "gcp_bare_metal_solution"
    """Google Bare Metal Solution (BMS)."""
    GCPCOMPUTEENGINE = "gcp_compute_engine"
    """Google Cloud Compute Engine (GCE)."""
    GCPCLOUDRUN = "gcp_cloud_run"
    """Google Cloud Run."""
    GCPKUBERNETESENGINE = "gcp_kubernetes_engine"
    """Google Cloud Kubernetes Engine (GKE)."""
    GCPCLOUDFUNCTIONS = "gcp_cloud_functions"
    """Google Cloud Functions (GCF)."""
    GCPAPPENGINE = "gcp_app_engine"
    """Google Cloud App Engine (GAE)."""
    GCPOPENSHIFT = "gcp_openshift"
    """Red Hat OpenShift on Google Cloud."""
    IBMCLOUDOPENSHIFT = "ibm_cloud_openshift"
    """Red Hat OpenShift on IBM Cloud."""
    TENCENTCLOUDCVM = "tencent_cloud_cvm"
    """Tencent Cloud Cloud Virtual Machine (CVM)."""
    TENCENTCLOUDEKS = "tencent_cloud_eks"
    """Tencent Cloud Elastic Kubernetes Service (EKS)."""
    TENCENTCLOUDSCF = "tencent_cloud_scf"
    """Tencent Cloud Serverless Cloud Function (SCF)."""


class CloudProviderValues(Enum):
    ALIBABACLOUD = "alibaba_cloud"
    """Alibaba Cloud."""
    AWS = "aws"
    """Amazon Web Services."""
    AZURE = "azure"
    """Microsoft Azure."""
    GCP = "gcp"
    """Google Cloud Platform."""
    HEROKU = "heroku"
    """Heroku Platform as a Service."""
    IBMCLOUD = "ibm_cloud"
    """IBM Cloud."""
    TENCENTCLOUD = "tencent_cloud"
    """Tencent Cloud."""
