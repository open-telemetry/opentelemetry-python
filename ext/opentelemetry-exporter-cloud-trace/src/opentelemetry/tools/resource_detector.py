import requests

from opentelemetry.sdk.resources import Resource, ResourceDetector

_GCP_METADATA_URL_HEADER = {"Metadata-Flavor": "Google"}


class GoogleResourceFinder:
    def __init__(self, base_url, url_post_process=None):
        self.base_url = base_url
        self.url_post_process = url_post_process or {}

    def get_attribute(self, attribute_url: str) -> str:
        """Fetch the requested instance metadata entry.

        :param attribute_url: suffix of the complete url
        :return:  The value read from the metadata service
        """
        attribute_value = requests.get(
            self.base_url + attribute_url, headers=_GCP_METADATA_URL_HEADER
        ).text

        if attribute_url in self.url_post_process:
            attribute_value = self.url_post_process[attribute_url](
                attribute_value
            )

        return attribute_value

    def get_resources(self):
        pass


class GCEResourceFinder(GoogleResourceFinder):
    """ Resource finder for common GCE attributes

    See: https://cloud.google.com/compute/docs/storing-retrieving-metadata
    """

    def __init__(self):
        super().__init__(
            "http://metadata.google.internal/computeMetadata/v1/",
            {
                # e.g. 'projects/233510669893/zones/us-east1-d' -> 'us-east1-d'
                "instance/zone": lambda v: v.split("/")[-1]
                if "/" in v
                else v
            },
        )
        self.attribute_key_to_url = {
            "cloud.account.id": "project/project-id",
            "host.id": "instance/id",
            "cloud.zone": "instance/zone",
        }

    def get_resources(self):
        # If we are currently not in a GCE instance this call will throw
        try:
            instance_id = self.get_attribute("instance/id")
        # pylint: disable=broad-except
        except Exception:
            instance_id = None
        if instance_id is None:
            return {}

        gce_resources = {"host.id": instance_id, "cloud.provider": "gcp"}
        for attribute_key, attribute_url in self.attribute_key_to_url.items():
            if attribute_key in gce_resources:
                continue
            gce_resources[attribute_key] = self.get_attribute(attribute_url)
        return gce_resources


_RESOURCE_TYPE_TO_FINDER = {"gce_instance": GCEResourceFinder}


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
                found_resources = resource_finder().get_resources()
                if found_resources:
                    self.gcp_resources[resource_type] = found_resources
        return Resource(self.gcp_resources)
