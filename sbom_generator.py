from requests import get
from ipdb import set_trace
from os import environ
from json import dumps


sbom_access_token = environ.get("SBOM_ACCESS_TOKEN")

if sbom_access_token is None:
    raise Exception("SBOM access token is not set")

headers = {
    'Authorization': f'Bearer {sbom_access_token}',
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

repo_owner = 'ocelotl'
repo_name = 'opentelemetry-python'

base_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}'
base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/dependency-graph/sbom"
base_url = "https://api.github.com/repos/open-telemetry/opentelemetry-python/dependency-graph/sbom"

contents_url = f'{base_url}/contents'
# result_list = get(contents_url, headers=headers).json()
result_list = get(base_url, headers=headers).json()

result_str = dumps(result_list, indent=4)

set_trace()

print(result_str)
