import requests

from opentelemetry.context import attach, detach, set_value
from opentelemetry.sdk.resources import Resource, ResourceDetector
import os

_GCP_METADATA_URL = (
    "http://metadata.google.internal/computeMetadata/v1/?recursive=true"
)
_GCP_METADATA_URL_HEADER = {"Metadata-Flavor": "Google"}

def _get_all_google_metadata():
    token = attach(set_value("suppress_instrumentation", True))
    all_metadata = requests.get(
        _GCP_METADATA_URL, headers=_GCP_METADATA_URL_HEADER
    ).json()
    detach(token)
    return all_metadata

def get_gce_resources():
    """ Resource finder for common GCE attributes

        See: https://cloud.google.com/compute/docs/storing-retrieving-metadata
    """
    all_metadata = _get_all_google_metadata()
    gce_resources = {
        "host.id": all_metadata["instance"]["id"],
        "cloud.account.id": all_metadata["project"]["projectId"],
        "cloud.zone": all_metadata["instance"]["zone"].split("/")[-1],
        "cloud.provider": "gcp",
        "gcp.resource_type": "gce_instance",
    }
    return gce_resources

def get_gke_resources():
    """ Resource finder for GKE attributes

    """
    all_metadata = _get_all_google_metadata()
    with open(
            '/var/run/secrets/kubernetes.io/serviceaccount/namespace') as namespace_file:
        pod_namespace = namespace_file.read().strip()
    with open('/etc/hostname', 'r') as name_file:
        pod_name = name_file.read().strip()
    gke_resources = {
        "cloud.account.id": all_metadata["project"]["projectId"],
        'k8s.cluster.name': all_metadata['instance']['attributes']['cluster-name'],
        'k8s.namespace.name': pod_namespace,
        "host.id": all_metadata["instance"]["id"],
        'k8s.pod.name': pod_name,
        'container.name': '',
        "cloud.zone": all_metadata["instance"]["zone"].split("/")[-1],
        "cloud.provider": "gcp",
        "gcp.resource_type": "gke_container",
    }
    return gke_resources



_RESOURCE_FINDERS = [get_gke_resources, get_gce_resources]


class GoogleCloudResourceDetector(ResourceDetector):
    def __init__(self, raise_on_error=False):
        super().__init__(raise_on_error)
        self.cached = False
        self.gcp_resources = {}

    def detect(self) -> "Resource":
        if not self.cached:
            self.cached = True
            for resource_finder in _RESOURCE_FINDERS:
                found_resources = resource_finder()
                if found_resources:
                    self.gcp_resources = found_resources
                    break
        return Resource(self.gcp_resources)
