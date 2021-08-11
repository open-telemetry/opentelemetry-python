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

from random import uniform, randint, choice


servers = {}


def check_server(function):

    def inner(server):

        if server not in servers.keys():

            servers[server] = {}

            if function.__name__ not in servers[server].keys():

                servers[server][function.__name__] = 0

        servers[server][function.__name__] = (
            servers[server][function.__name__] + function(server)
        )

    return inner


def temperature(server):

    return round(uniform(-5, 100), 2)


def humidity(server):

    return round(uniform(20, 30), 2)


@check_server
def cpu_usage(server):

    return round(uniform(20, 30), 2)


@check_server
def memory_usage(server):

    return randint(1000, 2000)


class Client:

    process_id_counter = 0
    port_counter = 5000

    def __init__(self):

        self.host_name = "hostname"
        self.process_id = Client.process_id_counter
        Client.process_id_counter = Client.process_id_counter + 1
        self.type = choice(["Android", "iOS"])
        self.http_flavor = "1.1"
        self.port_counter = Client.port_counter
        Client.port_counter = Client.port_counter + 1
        self.ip_address = "1.2.3.4"

    def get(self, server_address):
        pass

    def post(self, server_address):
        pass

    def put(self, server_address):
        pass


class Server:

    def __init__(self):
        self.ip_address = "5.6.7.8"
