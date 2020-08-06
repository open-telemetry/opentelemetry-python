import random
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np
from opentelemetry import metrics
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.sdk.metrics.export.aggregate import SumAggregator
from opentelemetry.sdk.metrics.export.controller import PushController
from opentelemetry.sdk.metrics.export.in_memory_metrics_exporter import (
    InMemoryMetricsExporter,
)
from opentelemetry.sdk.metrics.view import View, ViewConfig

# set up opentelemetry

# Sets the global MeterProvider instance
metrics.set_meter_provider(MeterProvider())

meter = metrics.get_meter(__name__)

# Export to a python list so we can do stats with the data
exporter = InMemoryMetricsExporter()

# instead of waiting for the controller to tick over time, we will just tick it ourselves
controller = PushController(meter, exporter, 500)

# Create the metric that we will use
bytes_counter = meter.create_metric(
    name="bytes_counter",
    description="Number of bytes received by service",
    unit="By",
    value_type=int,
    metric_type=Counter,
)

# Every time interval we will collect 100 exemplars statistically (selected without bias)
aggregator_config = {"num_exemplars": 100, "statistical_exemplars": True}

# Assign a Sum aggregator to `bytes_counter` that collects exemplars
counter_view = View(
    bytes_counter,
    SumAggregator,
    aggregator_config=aggregator_config,
    label_keys=["environment"],
    view_config=ViewConfig.LABEL_KEYS,
)

meter.register_view(counter_view)

# generate the random metric data


def unknown_customer_calls():
    """Generate customer call data to our application"""

    # set a random seed for consistency of data for example purposes
    np.random.seed(1)
    # Make exemplar selection consistent for example purposes
    random.seed(1)

    # customer 123 is a big user, and made 1000 requests in this timeframe
    requests = np.random.normal(
        1000, 100, 1000
    )  # 1000 requests with average 1000 bytes, standard deviation 100

    for request in requests:
        bytes_counter.add(
            int(request),
            {
                "environment": "production",
                "method": "REST",
                "customer_id": 123,
            },
        )

    # customer 247 is another big user, making fewer, but bigger requests
    requests = np.random.normal(
        5000, 1250, 200
    )  # 200 requests with average size of 5k bytes

    for request in requests:
        bytes_counter.add(
            int(request),
            {
                "environment": "production",
                "method": "REST",
                "customer_id": 247,
            },
        )

    # There are many other smaller customers
    for customer_id in range(250):
        requests = np.random.normal(1000, 250, np.random.randint(1, 10))
        method = "REST" if np.random.randint(2) else "gRPC"
        for request in requests:
            bytes_counter.add(
                int(request),
                {
                    "environment": "production",
                    "method": method,
                    "customer_id": customer_id,
                },
            )


unknown_customer_calls()

# Tick the controller so it sends metrics to the exporter
controller.tick()

# collect metrics from our exporter
metric_data = exporter.get_exported_metrics()

# get the exemplars from the bytes_in counter aggregator
aggregator = metric_data[0].aggregator
exemplars = aggregator.checkpoint_exemplars

# Sum up the total bytes in per customer from all of the exemplars collected
customer_bytes_map = defaultdict(int)
for exemplar in exemplars:
    customer_bytes_map[exemplar.dropped_labels] += exemplar.value


customer_bytes_list = sorted(
    customer_bytes_map.items(), key=lambda t: t[1], reverse=True
)

# Save our top 5 customers and sum all of the rest into "Others".
top_5_customers = [
    ("Customer {}".format(dict(val[0])["customer_id"]), val[1])
    for val in customer_bytes_list[:5]
] + [("Other Customers", sum([val[1] for val in customer_bytes_list[5:]]))]

# unzip the data into X (sizes of each customer's contribution) and labels
labels, X = zip(*top_5_customers)

# create the chart with matplotlib and show it
plt.pie(X, labels=labels)
plt.show()

# Estimate how many bytes customer 123 sent
customer_123_bytes = customer_bytes_map[
    (("customer_id", 123), ("method", "REST"))
]

# Since the exemplars were randomly sampled, all sample_counts will be the same
sample_count = exemplars[0].sample_count
full_customer_123_bytes = sample_count * customer_123_bytes

# With seed == 1 we get 1008612 - quite close to the statistical mean of 1000000! (more exemplars would make this estimation even more accurate)
print(
    "Customer 123 sent about {} bytes this interval".format(
        int(full_customer_123_bytes)
    )
)

# Determine the top 25 customers by how many bytes they sent in exemplars
top_25_customers = customer_bytes_list[:25]

# out of those 25 customers, determine how many used grpc, and come up with a ratio
percent_grpc = sum(
    1
    for customer_value in top_25_customers
    if customer_value[0][1][1] == "gRPC"
) / len(top_25_customers)

print(
    "~{}% of the top 25 customers (by bytes in) used gRPC this interval".format(
        int(percent_grpc * 100)
    )
)

# Determine the 50th, 90th, and 99th percentile of byte size sent in
quantiles = np.quantile(
    [exemplar.value for exemplar in exemplars], [0.5, 0.9, 0.99]
)
print("50th Percentile Bytes In:", int(quantiles[0]))
print("90th Percentile Bytes In:", int(quantiles[1]))
print("99th Percentile Bytes In:", int(quantiles[2]))
