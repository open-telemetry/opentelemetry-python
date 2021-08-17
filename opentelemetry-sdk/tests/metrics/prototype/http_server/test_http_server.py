from asyncio import sleep, gather, run, Queue, create_task
from random import random, seed, choice
from unittest import TestCase


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

    class Instrument:

        def __init__(self):
            self.tasks = []

        def add(self, task):
            self.tasks.append(task)

        def pop(self):
            self.tasks.pop()

    serving = Instrument()

    tester_queue = Queue()

    class Push:

        async def start(self):

            while True:
                await sleep(1)
                self.export()
                await tester_queue.put(serving.tasks)

    class Exporter:

        def export(self):
            print("Exported tasks: {}".format(serving.tasks))

    class TheExporter(Push, Exporter):
        pass

    the_exporter = TheExporter()

    class Tester(TestCase):

        async def test_http_proto(self):

            result = await tester_queue.get()
            assert result == [35, 34, 36]
            tester_queue.task_done()

            result = await tester_queue.get()
            assert result == [35]
            tester_queue.task_done()

            result = await tester_queue.get()
            assert result == [5]
            tester_queue.task_done()

    class Server:

        active_tasks = 0

        def __init__(self):
            self.address = 32
            self.queue = addresses_queues[self.address]

        async def serve(self):

            while True:

                address = await self.queue.get()
                Server.active_tasks = Server.active_tasks + 1
                serving.add(address)
                print("Real requests: {}".format(serving.tasks))
                # This is to simulate the different amounts of time it takes
                # for different requests to be processed by the server.
                await sleep(random())
                await addresses_queues[address].put(choice([200, 400]))
                Server.active_tasks = Server.active_tasks - 1
                serving.pop()
                print("Real requests: {}".format(serving.tasks))
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
