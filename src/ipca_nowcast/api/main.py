"""FastAPI application factory. Endpoints are added in phase F4."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ipca_nowcast import __version__
from ipca_nowcast.api.routes import router as api_router
from ipca_nowcast.config import get_settings
from ipca_nowcast.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="IPCA Nowcast API",
        version=__version__,
        description="Open-data Brazilian inflation nowcasting and backtesting.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()
