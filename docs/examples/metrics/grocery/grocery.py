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

from opentelemetry.metrics import get_meter_provider
from opentelemetry.sdk.metrics.export import ConsoleExporter

exporter = ConsoleExporter()

get_meter_provider().start_pipeline_equivalent(exporter, 5)

meter = get_meter_provider().get_meter()


order_counter = meter.create_counter(
    name="orders",
    description="number of orders",
    unit="order",
    value_type=int,
)

amount_counter = meter.create_counter(
    name="amount",
    description="amount paid",
    unit="dollar",
    value_type=int,
)

sold_items_counter = meter.create_counter(
    name="sold items",
    description="number of sold items",
    unit="item",
    value_type=int,
)

customers_in_store = meter.create_up_down_counter(
    name="customers in store",
    description="amount of customers present in store",
    unit="customer",
    value_type=int,
)


class GroceryStore:
    def __init__(self, name):
        self._name = name

    def process_order(self, customer_name, potatoes=0, tomatoes=0):
        order_counter.add(1, {"store": self._name, "customer": customer_name})

        amount_counter.add(
            (potatoes * 1) + (tomatoes * 3),
            {"store": self._name, "customer": customer_name},
        )

        sold_items_counter.add(
            potatoes,
            {
                "store": self._name,
                "customer": customer_name,
                "item": "potato",
            },
        )

        sold_items_counter.add(
            tomatoes,
            {
                "store": self._name,
                "customer": customer_name,
                "item": "tomato",
            },
        )

    def enter_customer(self, customer_name, account_type):

        customers_in_store.add(
            1, {"store": self._name, "account_type": account_type}
        )

    def exit_customer(self, customer_name, account_type):

        customers_in_store.add(
            -1, {"store": self._name, "account_type": account_type}
        )
