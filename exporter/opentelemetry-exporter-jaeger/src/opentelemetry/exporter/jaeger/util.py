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

import logging

from grpc import ChannelCredentials, ssl_channel_credentials

from opentelemetry.configuration import Configuration

logger = logging.getLogger(__name__)

DEFAULT_INSECURE = False


def _get_insecure(param):
    if param is not None:
        return param
    insecure_env = Configuration().get("EXPORTER_JAEGER_INSECURE", None)
    if insecure_env is not None:
        return insecure_env.lower() == "true"
    return DEFAULT_INSECURE


def _load_credential_from_file(path) -> ChannelCredentials:
    try:
        with open(path, "rb") as creds_file:
            credential = creds_file.read()
            return ssl_channel_credentials(credential)
    except FileNotFoundError:
        logger.exception("Failed to read credential file")
        return None


def _get_credentials(param):
    if param is not None:
        return param
    creds_env = Configuration().get("EXPORTER_JAEGER_CERTIFICATE", None)
    if creds_env:
        return _load_credential_from_file(creds_env)
    return ssl_channel_credentials()
