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


from unittest import TestCase

from opentelemetry.sdk.metrics.export import Exporter, Result

from opentelemetry.sdk.metrics.meter import MeterProvider


meter = MeterProvider().get_meter("meter")


class TestExporter(Exporter):

    def __init__(self, dictionary):
        self.dictionary = dictionary

    def export(self, records):

        for record in records:

            self.dictionary.update(record)

        return Result.SUCCESS


class Store:

    potato_price = 1
    tomato_price = 3

    def __init__(self, name):
        self.name = name
        self.number_of_orders = meter.create_counter(
            "number_of_orders",
            unit="orders",
            description="number of orders ordered by a store customer"
        )
        self.amount = meter.create_counter(
            "amount",
            unit="dollars",
            description="amount paid by a store customer"
        )
        self.items_sold = meter.create_counter(
            "items_sold",
            unit="items",
            description="items sold to a store customer"
        )

    def process_order(self, customer, potatoes=0, tomatoes=0):

        self.number_of_orders.add(1, store=self.name, customer=customer)
        self.amount.add(
            self.potato_price * potatoes + self.tomato_price * tomatoes,
            store=self.name,
            customer=customer
        )
        self.items_sold.add(
            potatoes, store=self.name, customer=customer, item="potato"
        )
        self.items_sold.add(
            tomatoes, store=self.name, customer=customer, item="tomato"
        )


store = Store("store")


class TestPrototype(TestCase):
    def test_prototype(self):
        store.process_order("customer0", potatoes=2, tomatoes=3)
        store.process_order("customer1", tomatoes=10)
        store.process_order("customer2", potatoes=2)
        store.process_order("customer0", tomatoes=1)

        records = {}
        TestExporter(records).export(meter.get_records())

        self.assertEqual(records, {})
