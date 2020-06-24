import requests

from opentelemetry.sdk.resources import Resource, ResourceDetector

_GCP_METADATA_URI = "http://metadata.google.internal/computeMetadata/v1/"
_GCP_METADATA_URI_HEADER = {"Metadata-Flavor": "Google"}

# GCE common attributes
# See: https://cloud.google.com/compute/docs/storing-retrieving-metadata
_GCE_ATTRIBUTES = {
    "project_id": "project/project-id",
    "instance_id": "instance/id",
    "zone": "instance/zone",
}

_ATTRIBUTE_URI_TRANSFORMATIONS = {
    "instance/zone": lambda v: v.split("/")[-1] if "/" in v else v
}

_GCP_METADATA_MAP = {}


class GoogleCloudResourceDetector(ResourceDetector):
    def __init__(self, crash_on_error=False):
        super().__init__(crash_on_error)
        self.scraped = False

    def _scrape_attributes(self) -> None:
        instance_id = self.get_attribute("instance/id")
        if instance_id is not None:
            _GCP_METADATA_MAP["instance_id"] = instance_id

            for attribute_key, attribute_uri in _GCE_ATTRIBUTES.items():
                if attribute_key in _GCP_METADATA_MAP:
                    continue
                _GCP_METADATA_MAP[attribute_key] = self.get_attribute(
                    attribute_uri
                )

    @staticmethod
    def get_attribute(attribute_uri: str) -> str:
        """Fetch the requested instance metadata entry.

        :param attribute_uri: attribute_uri: attribute name relative to the
        computeMetadata/v1 prefix
        :return:  The value read from the metadata service or None
        """
        attribute_value = requests.get(
            _GCP_METADATA_URI + attribute_uri, headers=_GCP_METADATA_URI_HEADER
        ).content

        if attribute_value is not None and isinstance(attribute_value, bytes):
            # At least in python3, the response is ISO-8859-1 encoded bytes
            attribute_value = attribute_value.decode("ISO-8859-1")

        if attribute_uri in _ATTRIBUTE_URI_TRANSFORMATIONS:
            attribute_value = _ATTRIBUTE_URI_TRANSFORMATIONS[attribute_uri](
                attribute_value
            )

        return attribute_value

    def detect(self) -> "Resource":
        if not self.scraped:
            self._scrape_attributes()
            self.scraped = True
        if _GCE_ATTRIBUTES:
            return Resource({"gce_instance": _GCP_METADATA_MAP})
        return Resource.create_empty()
