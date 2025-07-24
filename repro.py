# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "fastapi",
#     "opentelemetry-distro",
#     "opentelemetry-instrumentation",
#     "opentelemetry-exporter-otlp",
#     "uvicorn",
#     "opentelemetry-instrumentation-fastapi",
#     "opentelemetry-instrumentation-asgi",
#     "opentelemetry-util-http",
#     "opentelemetry-semantic-conventions",
# ]
# ///

import os
import logging
logging.basicConfig(level=0)
os.environ["OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED"] = "true"

from opentelemetry.instrumentation import auto_instrumentation
from opentelemetry._logs import (
    NoOpLogger,
    SeverityNumber,
    get_logger,
    get_logger_provider,
)
auto_instrumentation.initialize(swallow_exceptions=False)

import uvicorn

from fastapi import FastAPI

app = FastAPI()
print(logging.root.handlers)
@app.get("/")
async def root():
    logging.info("Handling request for root endpoint")
    return {"message": "Hello World"}

logging.info("AGJAJSGJAG")

uvicorn.run(app, host="0.0.0.0", port=3000)
print("RUNNING !")
# provider =  get_logger_provider()
# provider.shutdown()
