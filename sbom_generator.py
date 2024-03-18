from requests import get
from ipdb import set_trace
from os import environ
from json import dumps


sbom_access_token = environ.get("SBOM_ACCESS_TOKEN")

if sbom_access_token is None:
    raise Exception("SBOM access token is not set")

headers = {
    'Authorization': f'Bearer {sbom_access_token}'
}

repo_owner = 'ocelotl'
repo_name = 'opentelemetry-python'
base_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}'

contents_url = f'{base_url}/contents'
result_list = get(contents_url, headers=headers).json()

result_str = dumps(result_list, indent=4)

set_trace()

print(result_str)
