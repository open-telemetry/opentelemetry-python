# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""FastAPI application entry point (uninstrumented).

This is the plain version of the rolldice application without any
OpenTelemetry instrumentation.  Compare with the instrumented version
in the parent directory to see what OTel adds.
"""

import logging
import os

import uvicorn
from fastapi import FastAPI, Query, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from library import rolldice

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Rolldice",
    description="OpenTelemetry reference application — rolls a six-sided die.",
    version="0.1.0",
)


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
    rolls_raw = rolls if rolls is not None else "1"

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

    if rolls_int == 1:
        return PlainTextResponse(content=str(results[0]))
    return JSONResponse(content=results)


if __name__ == "__main__":
    port = int(os.environ.get("APPLICATION_PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
