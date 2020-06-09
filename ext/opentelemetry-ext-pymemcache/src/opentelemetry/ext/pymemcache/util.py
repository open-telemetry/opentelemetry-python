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
#

"""
Some utils used by the pymemcache integration
"""


# Network attribute semantic convention here:
# https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/trace/semantic_conventions/span-general.md#general-network-connection-attributes
_HOST = "net.peer.name"
_PORT = "net.peer.port"
# Database semantic conventions here:
# https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/trace/semantic_conventions/database.md
_DB = "db.type"
_URL = "db.url"


def _get_address_attributes(instance):
    """Attempt to get host and port from Client instance."""
    address_attributes = {}
    address_attributes[_DB] = "memcached"

    # client.base.Client contains server attribute which is either a host/port tuple, or unix socket path string
    # https://github.com/pinterest/pymemcache/blob/f02ddf73a28c09256589b8afbb3ee50f1171cac7/pymemcache/client/base.py#L228
    if hasattr(instance, "server"):
        if isinstance(instance.server, tuple):
            host, port = instance.server
            address_attributes[_HOST] = host
            address_attributes[_PORT] = port
            address_attributes[_URL] = "memcached://{}:{}".format(host, port)
        elif isinstance(instance.server, str):
            address_attributes[_URL] = "memcached://{}".format(instance.server)

    return address_attributes
