OpenTelemetry Env Propagator
===========================

This library provides a propagator to propagate trace/baggage details in a particular format (b3/w3c/any other)
from one process (invoking process) to the next (invoked process) using environment dictionary as the carrier.

Using environment dictionary as the carrier will help to connect batch processes.
For example: The environment dictionary containing trace/baggage details can be passed to the next process
in the subprocess call.
