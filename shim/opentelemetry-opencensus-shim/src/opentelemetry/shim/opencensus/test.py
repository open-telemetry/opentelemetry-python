
from opencensus.stats import stats as stats_module
from opentelemetry.shim.opencensus.metrics._producer import OpenCensusMetricProducer, Foo



mp = OpenCensusMetricProducer()
stats = stats_module.stats
x = Foo()
x.Foobar()

# Getting OpenCensus metrics
oc_metrics = stats.get_metrics()

# Converting OpenCensus metrics to OpenTelemetry metrics 
ot_metrics = mp.produce(oc_metrics)

# Printing the converted metrics
print(ot_metrics) 

