Metrics Plan API
================


This is the plan to define what tasks are pending to take our new metrics
implementation to its most possibly complete state.

Tasks
-----

#. Write API tests
#. Check API for completeness

MeterProvider
.............

#. Test the API provides a way to set and get a global default MeterProvider
#. Test that it is possible to create any number of MeterProviders
#. Test that the MeterProvider provides get_meter
#. Test that get_meter accepts name, version and schema_url
#. Test that when an invalid name is specified a working meter implementation
   is returned as a fallback.
#. Test that the fallback meter name property keeps its original invalid value.
#. Test that a message is logged reporting the specified value for the fallback
   meter is invalid.
#. Test that new configuration applies to previously returned meters.
#. Test that the effect of associating a schema URL with a meter is that the
   telemetry emitted using that meter is associated with the schema URL.

Meter
-----

#. Test that the meter provides functions to create a new Counter
#. Test that get_meter accepts name, version and schema_url
#. Test that when an invalid name is specified a working meter implementation
   is returned as a fallback.
#. Test that the fallback meter name property keeps its original invalid value.
#. Test that a message is logged reporting the specified value for the fallback
   meter is invalid.
#. Test that new configuration applies to previously returned meters.
#. Test that the effect of associating a schema URL with a meter is that the
   telemetry emitted using that meter is associated with the schema URL.

Meter
-----

#. Test that the meter provides functions to create a new Counter.
#. Test that the meter provides functions to create a new Asynchronous Counter.
#. Test that the meter provides functions to create a new Histogram.
#. Test that the meter provides functions to create a new Asynchronous Gauge.
#. Test that the meter provides functions to create a new Up down Counter.
#. Test that the meter provides functions to create a new Asynchronous Up down
   Counter.

Instrument
----------

#. Test that the instrument has name.
#. Test that the instrument has kind.
#. Test that the instrument has an optional unit of measure.
#. Test that the instrument has an optional description.
#. Test that the meter returns an error when multiple instruments are
   registered under the same Meter using the same name.
#. Test that is possible to register two instruments with the same name under
   different meters.
#. Test that instrument names conform to the specified syntax.
#. Test that instrument units conform to the specified syntax.
#. Test that instrument descriptions conform to the specified syntax.

Counter
-------

#. Test that the Counter can be created with create_counter.
#. Test that the API Counter is an abstract class.
#. Test that the API for creating a counter accepts the name of the instrument.
#. Test that the API for creating a counter accepts the unit of the instrument.
#. Test that the API for creating a counter accepts the description of the
   instrument.
#. Test that the counter has an add method.
#. Test that the add method returns None.
#. Test that the add method accepts optional attributes.
#. Test that the add method accepts the increment amount.
#. Test that the add method accepts only positive amounts.

Asynchronous Counter
--------------------

#. Test that the Counter can be created with create_asynchronous_counter.
#. Test that the API ObservableCounter is an abstract class.
#. Test that the API for creating a asynchronous counter accepts the name of
   the instrument.
#. Test that the API for creating a asynchronous counter accepts the unit of
   the instrument.
#. Test that the API for creating a asynchronous counter accepts the
   description of the instrument.
#. Test that the API for creating a asynchronous counter accepts a callback.
#. Test that the asynchronous counter has an add method.
#. Test that the add method returns None.
#. Test that the add method accepts optional attributes.
#. Test that the add method accepts the increment amount.
#. Test that the add method accepts only positive amounts.
#. Test that the callback function has a timeout.
#. Test that the callback function reports measurements.
#. Test that if multiple independent SDKs coexist in a running process, they
   invoke the callback functions independently.
#. Test that there is a way to pass state to the callback.

Concurrency
-----------

#. Test that all methods of MeterProvider are safe to be called concurrently.
#. Test that all methods of Meter are safe to be called concurrently.
#. Test that all methods of Instrument are safe to be called concurrently.
