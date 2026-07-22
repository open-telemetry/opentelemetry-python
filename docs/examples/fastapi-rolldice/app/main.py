# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""FastAPI application entry point for the rolldice reference application.

Start-up order matters for OpenTelemetry:
  1. ``app.telemetry`` must be imported first — it installs the SDK providers
     globally before anything else creates tracers or meters.
  2. FastAPIInstrumentor must be called after the app is created but still at
     import time (not inside a request handler) so it can patch the ASGI
     middleware correctly.
  3. Library objects (tracer, meter, metric instruments) are created at module
     import time in ``library.rolldice``; because telemetry is already
     configured by then, those calls immediately resolve to real SDK objects.
"""

import logging
import os

import uvicorn
from fastapi import FastAPI, Query, Response
from fastapi.responses import JSONResponse, PlainTextResponse

# Importing telemetry first ensures the SDK is initialized before the
# FastAPIInstrumentor (below) registers its ASGI middleware, and before
# library/rolldice.py creates its tracer and meter at module load time.
import app.telemetry  # noqa: F401, E402  # isort: skip

from library import rolldice  # noqa: E402

# FastAPIInstrumentor automatically wraps every FastAPI route with an HTTP
# server span.  It reads the ASGI scope to populate standard HTTP semantic
# convention attributes such as:
#   • http.request.method  (GET, POST, …)
#   • http.response.status_code
#   • url.path
#   • server.address / server.port
# It also propagates the W3C TraceContext from incoming request headers so
# that distributed traces connect across service boundaries.
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Rolldice",
    description="OpenTelemetry reference application — rolls a six-sided die.",
    version="0.1.0",
)

# instrument_app() wraps the FastAPI ASGI app with OTel middleware.  This must
# be called after the app object is created and before the first request is
# served.  The instrumentation is additive: manual spans created inside route
# handlers automatically become children of the HTTP span created here.
FastAPIInstrumentor.instrument_app(app)


@app.get("/rolldice")
@app.post("/rolldice")
async def rolldice_endpoint(
    rolls: str | None = Query(default=None),
    player: str | None = Query(default=None),
) -> Response:
    """Roll a six-sided die one or more times.

    Query parameters:
      - ``rolls``: number of dice to roll (default: 1, must be a positive integer)
      - ``player``: optional player name included in debug log output

    Returns a single number (1-6) when rolls is 1, or a JSON array of numbers
    when rolls > 1.
    """
    # Default to 1 roll when the parameter is omitted.
    rolls_raw = rolls if rolls is not None else "1"

    # Validate that the value is numeric before passing it to the library.
    # Non-numeric input is a client error (HTTP 400).
    try:
        rolls_int = int(rolls_raw)
    except ValueError:
        logger.warning(
            "HTTP 400: invalid rolls parameter %r (must be an integer)",
            rolls_raw,
        )
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "Parameter rolls must be a positive integer",
            },
        )

    # Delegate dice logic to the library module.  The library validates that
    # rolls > 0 and raises ValueError for non-positive values, which we map
    # to HTTP 500 per the reference application specification.
    try:
        results = rolldice.roll_dice(rolls_int, player)
    except ValueError as exc:
        logger.error(
            "HTTP 500: library raised ValueError for rolls=%d — %s",
            rolls_int,
            exc,
        )
        return PlainTextResponse(status_code=500, content="")

    logger.info(
        "HTTP 200: %s rolled %d die/dice → %s",
        player or "anonymous player",
        rolls_int,
        results,
    )

    # Return a single number when only one die was rolled, otherwise an array.
    if rolls_int == 1:
        return PlainTextResponse(content=str(results[0]))
    return JSONResponse(content=results)


if __name__ == "__main__":
    # APPLICATION_PORT lets operators change the listening port without
    # modifying code, e.g. when running inside a container.
    port = int(os.environ.get("APPLICATION_PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
