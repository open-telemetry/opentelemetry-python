from json import dumps

from requests import get

with open("opentelemetry-python.spdx.json", "w") as sbom_file:
    sbom_file.write(
        dumps(
            get(
                (
                    "https://api.github.com/repos/open-telemetry/"
                    "opentelemetry-python/dependency-graph/sbom"
                ),
                headers={
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            ).json(),
            indent=4,
        )
    )
