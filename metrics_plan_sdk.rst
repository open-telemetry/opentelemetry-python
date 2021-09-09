Metrics Plan SDK
================


This is the plan to define what tasks are pending to take our new metrics
implementation to its most possibly complete state.

Tasks
-----

#. Write SDK tests
#. Check SDK for completeness

MeterProvider
.............

#. Test MeterProvider allows a Resource to be specified.
#. Test that a specified Resource can be associated with all the produced
   metrics from any Meter from the MeterProvider.
#. Test that the supplied name, version and schema_url arguments passed to the
   MeterProvider are used to create an InstrumentationLibrary instance stored
   in the Meter.
#. Test that configuration can be managed by the MeterProvider.
#. Test that the MeterProvider provides methods to update the configuration
#. Test that the updated configuration applies to all already returned Meters.


View
....

#. Test that there is a way to register Views with a MeterProvider
#. Test that the view instrument selection criteria is as specified.
#. Test that the name of the View can be specified.
#. Test that the configuration for the metrics stream is as specified.
#. Test that the specified logic is used to process Measurements made by
   an instrument.

Aggregation
...........

#. Test that the None aggregation is available.
#. Test that the None aggregation drops all measurements.
#. Test that the Default aggregation is available.
#. Test that the Default aggregation uses the specified aggregation.
#. Test that the Sum aggregation is available.
#. Test that the Sum aggregation performs as specified.
#. Test that the Last Value aggregation is available.
#. Test that the Last Value  aggregation performs as specified.
#. Test that the Histogram aggregation is available.
#. Test that the Histogram  aggregation performs as specified.
#. Test that the Explicit Bucket Histogram aggregation is available.
#. Test that the Explicit Bucket Histogram  aggregation performs as specified.

Measurement Processor
.....................

#. Test that a MeasurementProcessor allows hooks when a Measurement is recorded
   by an instrument.
#. Test that a MeasurementProcessor has access to the Measurement, Instrument
   and Resource.
#. Test that if a Measurement is reported by a synchronous Instrument, then a
   MeasurementProcessor has access to the Baggage, Context and Span associated
   with the Measurement.

Exemplars
.........

#. Test that the metric SDK provides a mechanism to sample Exemplars from
   measurements.
#. Test that the SDK allows an exemplar to be disabled.
#. Test that a disabled exemplar does not cause any overhead.
#. Test that by default the SDK only samples exemplars from the context of a
   sampled trace
#. Test that exemplar sampling can leverage the configuration of a metric
   aggregator.
#. Test that the SDK provides extensible Exemplar sampling hooks.
#. Test that the SDK provides an ExemplarFilter sampling hook.
#. Test that the SDK provides an ExemplarReservoir sampling hook.

Exemplar Filter
...............

#. Test that the Exemplarfilter provides a method to determine if a measurement
   should be sampled.
#. Test that the interface has access to the value of the measurement, the
   complete set of attributes of the measurement, the context of the
   measurement and the timestamp of the measurement.

Exemplar Reservoir
..................

#. Test that the ExemplarReservoir interface provides a method to offer
   measurements to the reservoir and another to collect accumulated Exemplars.
#. Test that the offer method accepts measurements including value, Attributes,
   Context and timestamp.
#. Test that the offer method has the ability to pull associated trace and
   span information without needing to record full context.
#. Test that the offer method does not need to store all measurements it is
   given and can further sample beyond the ExemplarFilter.
#. Test that the collect method returns accumulated Exemplars.
#. Test that Exemplars retain any attributes available in the measurement that
   are not preserved by aggregation or view configuration.
#. Test that joining together attributes on an Exemplar with those available
   on its associated metric data point result in the full set of attributes
   from the original sample measurement.
#. Test that the ExemplarReservoir avoids allocations when sampling exemplars.

Exemplar Defaults
.................

#. Test that the SDK includes a SimpleFixedSizeExemplarReservoir.
#. Test that the SDK includes an AlignedHistogramBucketExemplarReservoir.
#. Test that by default fixed sized histogram aggregators use
   AlignedHistogramBucketExemplarReservoir.
#. Test that all other aggregators use SimpleFixedSizeExemplarReservoir.
#. Test that the SimpleFixedSizeExemplarReservoir takes a configuration
   parameter for the size of the reservoir pool.
#. Test that the reservoir will accept measurements using an equivalent of the
   naive reservoir sampling algorithm.
#. Test that the AlignedHistogramBucketExemplarReservoir takes a configuration
   parameter that is the configuration of an Histogram.
#. Test that the implementation keeps the last seen measurement that falls
   within an Histogram bucket.
#. Test that the reservoir will accept measurements by using the equivalent of
   the specified naive algorithm.

Metric Exporter
...............

#. Test that the metric exporter has access to the pre aggregated metrics data
#. Test that the SDK provides a Push and a Pull Metric Exporter.
#. Test that the Push exporter provides an export function.
#. Test that the Push exporter export function can not be called concurrently
   from the same exporter instance.
#. Test that the Push exporter export function does not block indefinitely.
#. Test that the Push exporter export funtion receives a batch of metrics.
#. Test that the Push exporter export funtion returns Success or Failure.
#. Test that the Push exporter provides a ForceFlush function.
#. Test that the Push exporter ForceFlush can inform the caller wether it
   succeded, failed or timed out.
#. Test that the Push exporter provides a ForceFlush function.
#. Test that the Push exporter provides a shutdown function.
#. Test that the Push exporter shutdown function return Failure after being
   called once.
#. Test that the Push exporter shutdown function do not block indefinitely.

Defaults and Configuration
..........................

#. Test that the SDK provides OTEL_METRICS_EXEMPLAR_FILTER.
#. Test that the default value for OTEL_METRICS_EXEMPLAR_FILTER is
   WITH_SAMPLED_TRACE.
#. Test that the value of NONE for OTEL_METRICS_EXEMPLAR_FILTER causes no
   measurements to be eligble for exemplar sampling.
#. Test that the value of ALL for OTEL_METRICS_EXEMPLAR_FILTER causes all
   measurements to be eligble for exemplar sampling.
#. Test that the value of WITH_SAMPLED_TRACE for OTEL_METRICS_EXEMPLAR_FILTER
   causes only measurements s with a sampled parent span in context to be
   eligble for exemplar sampling.
