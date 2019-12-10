from opentelemetry.ext.flask import patch

try:
    patch()

except Exception as error:

    print(error)
