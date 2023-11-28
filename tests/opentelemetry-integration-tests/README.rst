OpenTelemetry Integration Tests
============================

This package contains longer-running OTel Python tests that often require additional services. These tests are
configured to be tox "additional environments" and therefore do not run by default. To run them run
`tox -e pyXX-integration-tests` e.g. `tox -e py38-integration-tests`.

References
----------
* `OpenTelemetry Project <https://opentelemetry.io/>`_
