import requests

from opentelemetry.sdk.resources import Resource, ResourceDetector

_GCE_METADATA_URL = (
    "http://metadata.google.internal/computeMetadata/v1?recursive=true"
)
_GCP_METADATA_URL_HEADER = {"Metadata-Flavor": "Google"}


def get_gce_resources():
    """ Resource finder for common GCE attributes

        See: https://cloud.google.com/compute/docs/storing-retrieving-metadata
    """
    # This call will throw if we aren't currently in a GCE instance
    try:
        all_metadata = requests.get(
            _GCE_METADATA_URL, headers=_GCP_METADATA_URL_HEADER
        ).json()
    # pylint: disable=broad-except
    except Exception:
        return {}
    gce_resources = {
        "host.id": all_metadata["instance"]["id"],
        "cloud.account.id": all_metadata["project"]["projectId"],
        "cloud.zone": all_metadata["instance"]["zone"].split("/")[-1],
        "cloud.provider": "gcp",
        "gcp.resource_type": "gce_instance",
    }
    return gce_resources


_RESOURCE_TYPE_TO_FINDER = {"gce_instance": get_gce_resources}


class GoogleCloudResourceDetector(ResourceDetector):
    def __init__(self, raise_on_error=False):
        super().__init__(raise_on_error)
        self.cached = False
        self.gcp_resources = {}

    def detect(self) -> "Resource":
        if not self.cached:
            self.cached = True
            for (
                resource_type,
                resource_finder,
            ) in _RESOURCE_TYPE_TO_FINDER.items():
                found_resources = resource_finder()
                if found_resources:
                    self.gcp_resources[resource_type] = found_resources
        return Resource(self.gcp_resources)
