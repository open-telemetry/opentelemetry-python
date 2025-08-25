# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from os import environ
from typing import Literal, Optional

import requests

from opentelemetry.sdk.environment_variables import (
    OTEL_PYTHON_EXPORTER_OTLP_CREDENTIAL_PROVIDER,
    OTEL_PYTHON_EXPORTER_OTLP_LOGS_CREDENTIAL_PROVIDER,
    OTEL_PYTHON_EXPORTER_OTLP_METRICS_CREDENTIAL_PROVIDER,
    OTEL_PYTHON_EXPORTER_OTLP_TRACES_CREDENTIAL_PROVIDER,
)
from opentelemetry.util._importlib_metadata import entry_points


def _is_retryable(resp: requests.Response) -> bool:
    if resp.status_code == 408:
        return True
    if resp.status_code >= 500 and resp.status_code <= 599:
        return True
    return False


def _load_session_from_envvar(
    exporter_type: Literal["logs", "traces", "metrics"],
) -> Optional[requests.Session]:
    if exporter_type == "logs":
        env_var = OTEL_PYTHON_EXPORTER_OTLP_LOGS_CREDENTIAL_PROVIDER
    elif exporter_type == "traces":
        env_var = OTEL_PYTHON_EXPORTER_OTLP_TRACES_CREDENTIAL_PROVIDER
    else:
        env_var = OTEL_PYTHON_EXPORTER_OTLP_METRICS_CREDENTIAL_PROVIDER
    credential_env = environ.get(
        OTEL_PYTHON_EXPORTER_OTLP_CREDENTIAL_PROVIDER
    ) or environ.get(env_var)
    if credential_env:
        try:
            maybe_session = next(
                iter(
                    entry_points(
                        group="opentelemetry_otlp_credential_provider",
                        name=credential_env,
                    )
                )
            ).load()("HTTP")
        except StopIteration:
            raise RuntimeError(
                f"Requested component '{credential_env}' not found in "
                f"entry point 'opentelemetry_otlp_credential_provider'"
            )
        if isinstance(maybe_session, requests.Session):
            print("returning session !!")
            return maybe_session
    return None
