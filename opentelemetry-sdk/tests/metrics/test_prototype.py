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

    def __init__(self, records):
        self.records = records

    def export(self, records):

        self.records.update(records)

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
        if bool(potatoes):
            self.items_sold.add(
                potatoes, store=self.name, customer=customer, item="potato"
            )
        if bool(tomatoes):
            self.items_sold.add(
                tomatoes, store=self.name, customer=customer, item="tomato"
            )


store = Store("store")


class TestPrototype(TestCase):
    def test_prototype(self):
        self.maxDiff = None
        store.process_order("customer0", potatoes=2, tomatoes=3)
        store.process_order("customer1", tomatoes=10)
        store.process_order("customer2", potatoes=2)
        store.process_order("customer0", tomatoes=1)

        records = {}
        TestExporter(records).export(meter.get_records())

        self.assertEqual(
            records,
            {
                "Counter": {
                    "number_of_orders": {
                        frozenset(
                            {('store', 'store'), ('customer', 'customer0')}
                        ): 2,
                        frozenset(
                            {('store', 'store'), ('customer', 'customer1')}
                        ): 1,
                        frozenset(
                            {('store', 'store'), ('customer', 'customer2')}
                        ): 1,
                    },
                    "amount": {
                        frozenset(
                            {('store', 'store'), ('customer', 'customer0')}
                        ): 14,
                        frozenset(
                            {('customer', 'customer1'), ('store', 'store')}
                        ): 30,
                        frozenset(
                            {('store', 'store'), ('customer', 'customer2')}
                        ): 2,
                    },
                    "items_sold": {
                        frozenset(
                            {
                                ('item', 'potato'),
                                ('store', 'store'),
                                ('customer', 'customer0')
                            }
                        ): 2,
                        frozenset(
                            {
                                ('item', 'tomato'),
                                ('store', 'store'),
                                ('customer', 'customer0')
                            }
                        ): 4,
                        frozenset(
                            {
                                ('customer', 'customer1'),
                                ('item', 'tomato'),
                                ('store', 'store')
                            }
                        ): 10,
                        frozenset(
                            {
                                ('item', 'potato'),
                                ('store', 'store'),
                                ('customer', 'customer2')
                            }
                        ): 2,
                    }
                }
            }
        )
