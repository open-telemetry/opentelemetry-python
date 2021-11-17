from time import time_ns
from typing import Iterable

from opentelemetry.sdk._metrics import MeterProvider, MetricReader
from opentelemetry._metrics.measurement import Measurement
from opentelemetry.sdk._metrics.export import AggregationTemporality
from opentelemetry.sdk._metrics.view import View, ViewSelector
from opentelemetry.sdk.resources import Resource


def observe_something() -> Iterable[Measurement]:
    yield Measurement(32, {"foo": "bar"})


def main() -> None:
    reader1 = MetricReader(
        preferred_temporality=AggregationTemporality.CUMULATIVE
    )
    reader2 = MetricReader(preferred_temporality=AggregationTemporality.DELTA)

    meter_provider = MeterProvider(
        metric_readers=[reader1, reader2],
        resource=Resource.create({"hello": "world"}),
        views=[
            # Three different names for the same request count
            View(
                name="request_count1",
                selector=ViewSelector(instrument_name="app.request_count"),
            ),
            View(
                name="request_count2",
                selector=ViewSelector(instrument_name="app.request_count"),
            ),
            # Rename the async counter just because
            View(
                name="app.somethingrename",
                selector=ViewSelector(instrument_name="app.something"),
            ),
        ],
    )
    meter = meter_provider.get_meter("foo", "1.0.0")

    meter.create_observable_counter(
        "app.something", callback=observe_something
    )
    meter.create_observable_gauge("app.mygauge", callback=observe_something)
    counter = meter.create_counter(
        "app.request_count", "The number of requests app has received"
    )

    print("add 21")
    counter.add(21)
    print("Cumulative:")
    for m in reader1.collect():
        print(m)
    print("\n\nDelta")
    for m in reader2.collect():
        print(m)

    print("\n\nDelta")
    for m in reader2.collect():
        print(m)
    print("add 21")
    counter.add(21)
    print("add 10")
    counter.add(10)
    print("\n\nCumulative")
    for m in reader1.collect():
        print(m)
    print("\n\nDelta")
    for m in reader2.collect():
        print(m)

    for _ in range(10):
        counter.add(1, {"color": "green"})
        counter.add(2, {"color": "yellow"})

    start = time_ns()
    reader1.collect()
    print(f"Reader1 collection took {time_ns() - start} nanos")
    start = time_ns()
    reader2.collect()
    print(f"Reader2 collection took {time_ns() - start} nanos")


if __name__ == "__main__":
    main()
