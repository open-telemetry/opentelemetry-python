from asyncio import sleep, gather, run, Queue, create_task
from random import random, seed, choice, randint
from unittest import TestCase

from opentelemetry.sdk.metrics.meter import MeterProvider

from opentelemetry.sdk.metrics.aggregator import LastAggregator


seed(3)


async def main():
    addresses_queues = {
        32: Queue(),
        33: Queue(),
        34: Queue(),
        35: Queue(),
        36: Queue(),
        37: Queue(),
    }

    meter = MeterProvider().get_meter("meter")

    active_requests = meter.create_up_down_counter(
        "active_requests",
        unit="active requests",
        description="Currently active requests"
    )

    humidity = meter.create_counter(
        "humidity",
        unit="percentage",
        description="Server humidity",
        aggregator_class=LastAggregator
    )

    temperature = meter.create_up_down_counter(
        "temperature",
        unit="F",
        description="Server temperature",
        aggregator_class=LastAggregator
    )

    tester_queue = Queue()

    class Push:

        async def start(self):

            while True:
                await sleep(1)
                self.export()
                await tester_queue.put(
                    active_requests.value(host_name="MachineA")
                )

    class Exporter:

        def export(self):
            from ipdb import set_trace
            set_trace
            print(
                "Exported active requests: {}".format(
                    active_requests.value(host_name="MachineA")
                )
            )

    class TheExporter(Push, Exporter):
        pass

    the_exporter = TheExporter()

    class Tester(TestCase):

        async def test_http_proto(self):

            result = await tester_queue.get()
            assert result == 2
            tester_queue.task_done()

            result = await tester_queue.get()
            assert result == 0
            tester_queue.task_done()

            result = await tester_queue.get()
            assert result == 0
            tester_queue.task_done()

    class Server:

        def __init__(self):
            self.address = 32
            self.queue = addresses_queues[self.address]

        async def serve(self):

            while True:

                address = await self.queue.get()
                active_requests.add(
                    1, host_name="MachineA"
                )
                humidity.add(randint(0, 100), host_name="MachineA")
                temperature.add(randint(-20, 100), host_name="MachineA")
                print(
                    "Served active Requests: {}".format(
                        active_requests.value(host_name="MachineA")
                    )
                )
                # This is to simulate the different amounts of time it takes
                # for different requests to be processed by the server.
                await sleep(random())
                await addresses_queues[address].put(choice([200, 400]))
                active_requests.add(-1, host_name="MachineA")
                print(
                    "Served active requests: {}".format(
                        active_requests.value(host_name="MachineA")
                    )
                )
                self.queue.task_done()

    class Client:

        def __init__(self, address):

            self.address = address
            self.queue = addresses_queues[self.address]
            self.padding = "             " * (self.address - 33)

        async def request(self):
            # This is to simulate the different times at which requests are
            # sent to the server.
            await sleep(random())
            print(
                f"\033[{self.address}m{self.padding}"
                f"client_{self.address} request starts"
            )
            await addresses_queues[32].put(self.address)

            result = await self.queue.get()
            print(
                f"\033[{self.address}m{self.padding}"
                f"client_{self.address} request ends"
            )
            print(
                f"\033[{self.address}m{self.padding}"
                f"client_{self.address} result: {result}"
            )
            self.queue.task_done()

    server_0 = create_task(Server().serve())
    server_1 = create_task(Server().serve())
    server_2 = create_task(Server().serve())
    exporter = create_task(the_exporter.start())

    await gather(
        *[
            Client(33).request(),
            Client(34).request(),
            Client(35).request(),
            Client(36).request(),
            Client(37).request(),
            Tester().test_http_proto()
        ]
    )

    for queue in addresses_queues.values():
        await queue.join()

    await tester_queue.join()

    server_0.cancel()
    server_1.cancel()
    server_2.cancel()
    exporter.cancel()


class TestHTTPServerClient(TestCase):
    def test_case(self):

        run(main())


if __name__ == "__main__":
    run(main())
