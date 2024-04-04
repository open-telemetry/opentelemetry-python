#!/bin/bash
# this is how i generated the type-ignore fixme comments automatically.
# planning to remove this after or I can move it to scripts dir

export MYPYPATH=$PWD/opentelemetry-api/src/:$PWD/opentelemetry-sdk/src/:$PWD/tests/opentelemetry-test-utils/src/:$PWD/opentelemetry-semantic-conventions/src/

# src
.tox/mypysdk/bin/mypy --namespace-packages --explicit-package-bases --show-error-codes opentelemetry-sdk/src/opentelemetry/ > mypy_report.txt
mypy-upgrade --summarize -r mypy_report.txt --fix-me '<will add tracking issue num>'

# tests
# .tox/mypysdk/bin/mypy --namespace-packages --show-error-codes --config-file=mypy-relaxed.ini opentelemetry-sdk/tests/ > mypy_report.txt
# mypy-upgrade --summarize -r mypy_report.txt --fix-me '<will add tracking issue num>'
