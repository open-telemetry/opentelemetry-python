# Fix Changelog

## Problem

The Django instrumentation documentation example in `docs/examples/django/manage.py` did not produce any OpenTelemetry output to STDOUT, despite the documentation (README.rst) claiming it would show JSON span data.

When users followed the example:
1. Installed `opentelemetry-sdk`, `opentelemetry-instrumentation-django`, and `requests`
2. Added `DjangoInstrumentor().instrument()` to their `manage.py`
3. Ran `python manage.py runserver`
4. Made HTTP requests to the server

**Expected**: JSON span output in the console showing trace information
**Actual**: No OpenTelemetry output was visible

## Root Cause

The Django example's `manage.py` was calling `DjangoInstrumentor().instrument()` to instrument the Django application, but it was missing the essential setup for tracing:

1. **No TracerProvider**: Without setting up a `TracerProvider`, the instrumentation has no way to create and manage spans properly.
2. **No SpanProcessor/Exporter**: Without a `SpanProcessor` with a `ConsoleSpanExporter`, captured traces have nowhere to be exported - they are effectively discarded.

This is in contrast to the Flask example (`docs/getting_started/flask_example.py`) which correctly includes both `TracerProvider` setup and `BatchSpanProcessor(ConsoleSpanExporter())` configuration.

## What Changed

### Files Modified

1. **`docs/examples/django/manage.py`**
   - Added imports for:
     - `from opentelemetry import trace`
     - `from opentelemetry.sdk.trace import TracerProvider`
     - `from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter`
   - Added TracerProvider and SpanProcessor setup before `DjangoInstrumentor().instrument()`:
     ```python
     trace.set_tracer_provider(TracerProvider())
     trace.get_tracer_provider().add_span_processor(
         BatchSpanProcessor(ConsoleSpanExporter())
     )
     ```

2. **`docs/examples/django/README.rst`**
   - Updated documentation to explain the three required steps for seeing span output:
     1. Set up a `TracerProvider`
     2. Add a `SpanProcessor` with an exporter (e.g., `ConsoleSpanExporter`)
     3. Call `DjangoInstrumentor().instrument()`
   - Added a code example showing the complete setup
   - Added explanation that without the TracerProvider and SpanProcessor setup, traces are captured but not exported

## Tests Added or Updated

No new tests were added as this is a documentation fix. The existing test infrastructure for `getting_started` examples was verified:

- `tox -e ruff` - PASSED (linting)
- `tox -e py312-test-opentelemetry-sdk` - PASSED (636 tests)

The Flask test failure observed during testing (`test_flask.py`) is due to network restrictions in the test environment (unable to reach `www.example.com`), not related to this fix.

## Backward Compatibility

This change has **no backward compatibility concerns**:

- The fix only adds functionality to the documentation example
- No existing APIs or behaviors are changed
- Users who already have working Django instrumentation will not be affected
- The change aligns the Django example with the existing Flask example pattern

## Migration Steps

For users who were following the original documentation:

1. Update your Django `manage.py` to include the TracerProvider setup:

   ```python
   import os
   import sys

   from opentelemetry import trace
   from opentelemetry.instrumentation.django import DjangoInstrumentor
   from opentelemetry.sdk.trace import TracerProvider
   from opentelemetry.sdk.trace.export import (
       BatchSpanProcessor,
       ConsoleSpanExporter,
   )

   def main():
       os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
       
       # Set up tracing with console exporter to see spans in stdout
       trace.set_tracer_provider(TracerProvider())
       trace.get_tracer_provider().add_span_processor(
           BatchSpanProcessor(ConsoleSpanExporter())
       )
       
       # Instrument Django
       DjangoInstrumentor().instrument()
       
       # ... rest of your Django setup
   ```

2. Run your Django app: `python manage.py runserver --noreload`

3. Make HTTP requests and you should now see JSON span output in your console
