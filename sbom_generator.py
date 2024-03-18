import requests
import json

# Authentication
headers = {
    'Authorization': 'Bearer YOUR_ACCESS_TOKEN'
}

# Repository information
repo_owner = 'open-telemetry'
repo_name = 'opentelemetry-python'
base_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}'
base_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}'

# Get repository contents
contents_url = f'{base_url}/contents'
repo_contents = requests.get(contents_url, headers=headers).json()

# List to store dependency information
dependencies = []

# Look for dependency files
dependency_files = [
    'requirements.txt', 'setup.py', 'Pipfile', 'requirements.in'
]

for file_data in repo_contents:
    if file_data['name'] in dependency_files:
        file_content = requests.get(
            file_data['download_url'], headers=headers
        ).text
        # Parse dependency information
        # Example: Extract dependencies from requirements.txt
        if file_data['name'] == 'requirements.txt':
            dependencies.extend(file_content.strip().split('\n'))

# Generate SBOM file (dummy example)
sbom_content = json.dumps({'dependencies': dependencies}, indent=4)

# Write SBOM to file
with open('sbom.json', 'w') as sbom_file:
    sbom_file.write(sbom_content)

print("SBOM file generated successfully.")
