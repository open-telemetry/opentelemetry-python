# This script is to be used by maintainers by running it locally.

from json import dumps
from os import environ

from requests import put
from yaml import safe_load

job_names = ["EasyCLA"]

# Check that the files below are all the workflow YAML files that should be
# considered.
for yml_file_name in [
    "test_0",
    "test_1",
    "misc_0",
    "lint_0",
    "contrib_0",
    "check-links",
]:
    with open(f"../.github/workflows/{yml_file_name}.yml") as yml_file:
        job_names.extend(
            [job["name"] for job in safe_load(yml_file)["jobs"].values()]
        )

owner = "open-telemetry"
repo = "opentelemetry-python"
branch = "main"

response = put(
    (
        f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}/"
        "protection/required_status_checks/contexts"
    ),
    headers={
        "Accept": "application/vnd.github.v3+json",
        # The token has to be created in Github, and exported to the
        # environment variable below. When creating the token, the resource
        # owner must be open-telemetry, the access must be for the repo above,
        # and read and write permissions must be granted for administration
        # permissions and read permissions must be granted for metadata
        # permissions.
        "Authorization": f"token {environ.get('REQUIRED_CHECKS_TOKEN')}",
    },
    data=dumps({"contexts": job_names}),
)

if response.status_code == 200:
    print(response.content)
else:
    print(
        "Failed to update branch protection settings. "
        f"Status code: {response.status_code}"
    )
    print(response.json())
