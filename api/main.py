"""FastAPI application for the fast-f1 analytics API.

Run locally:
    uvicorn api.main:app --reload

The app is a thin, read-only HTTP surface over the same ``services`` /
``f1_data`` layer the CLI and dashboard use — no analytics logic is
duplicated here, and no fabricated success responses are returned: when
data can't be retrieved, the specific service exception is mapped to an
honest HTTP error status.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

import config
from api.routes import info, races, seasons
from services import (
    DataSourceError,
    DataUnavailableError,
    InvalidQueryError,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="fast-f1 analytics API",
        version="0.1.0",
        description="Read-only Formula 1 analytics over FastF1 + Ergast.",
    )

    # Configure logging + FastF1 cache the same way as the CLI.
    config.setup()

    # Map specific service errors to honest HTTP status codes.
    error_map = {
        InvalidQueryError: 400,
        DataUnavailableError: 404,
        DataSourceError: 502,
    }

    for exc_type, status in error_map.items():

        def _handler_factory(status_code):
            def _handler(request, exc):
                return JSONResponse(
                    status_code=status_code,
                    content={"detail": str(exc), "error_type": type(exc).__name__},
                )

            return _handler

        app.add_exception_handler(exc_type, _handler_factory(status))

    app.include_router(info.router)
    app.include_router(seasons.router)
    app.include_router(races.router)

    return app


app = create_app()
