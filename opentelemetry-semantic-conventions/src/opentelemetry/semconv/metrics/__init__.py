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

# pylint: disable=too-many-lines


class MetricInstruments:

    HTTP_SERVER_DURATION = "http.server.duration"
    """
    Deprecated. Use `http.server.request.duration` metric.
    """

    HTTP_SERVER_REQUEST_SIZE = "http.server.request.size"
    """
    Deprecated. Use `http.server.request.body.size` metric.
    """

    HTTP_SERVER_RESPONSE_SIZE = "http.server.response.size"
    """
    Deprecated. Use `http.server.response.body.size` metric.
    """

    HTTP_CLIENT_DURATION = "http.client.duration"
    """
    Deprecated. Use `http.client.request.duration` metric.
    """

    HTTP_CLIENT_REQUEST_SIZE = "http.client.request.size"
    """
    Deprecated. Use `http.client.response.body.size` metric.
    """

    HTTP_CLIENT_RESPONSE_SIZE = "http.client.response.size"
    """
    Deprecated. Use `http.client.response.body.size` metric.
    """

    HTTP_SERVER_REQUEST_DURATION = "http.server.request.duration"

    HTTP_SERVER_REQUEST_BODY_SIZE = "http.server.request.body.size"

    HTTP_SERVER_RESPONSE_BODY_SIZE = "http.server.response.body.size"

    HTTP_SERVER_ACTIVE_REQUESTS = "http.server.active_requests"

    HTTP_CLIENT_REQUEST_DURATION = "http.client.request.duration"

    HTTP_CLIENT_REQUEST_BODY_SIZE = "http.client.request.body.size"

    HTTP_CLIENT_RESPONSE_BODY_SIZE = "http.client.response.body.size"

    DB_CLIENT_CONNECTIONS_USAGE = "db.client.connections.usage"
