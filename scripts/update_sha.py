import argparse
import requests
from ruamel.yaml import YAML

API_URL = "https://api.github.com/repos/open-telemetry/opentelemetry-python-contrib/commits/"
WORKFLOW_FILE = ".github/workflows/test.yml"

def get_sha(branch):
    url = API_URL + branch
    response = requests.get(url)
    response.raise_for_status()
    return response.json()["sha"]

def update_sha(sha):
    yaml = YAML()
    yaml.preserve_quotes = True
    with open(WORKFLOW_FILE, "r") as file:
        workflow = yaml.load(file)
    workflow["env"]["CONTRIB_REPO_SHA"] = sha
    with open(WORKFLOW_FILE, "w") as file:
        yaml.dump(workflow, file)

def main():
    args = parse_args()
    sha = get_sha(args.branch)
    update_sha(sha)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Updates the SHA in the workflow file"
    )
    parser.add_argument("-b", "--branch", help="branch to use")
    return parser.parse_args()

if __name__ == "__main__":
    main()
