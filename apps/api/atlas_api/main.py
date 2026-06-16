from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from atlas_api import __version__
from atlas_api.api.router import api_router
from atlas_api.core.config import get_settings
from atlas_api.core.errors import AtlasError, atlas_error_handler, unhandled_error_handler
from atlas_api.core.logging import configure_logging
from atlas_api.services.store import store


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Atlas API",
        version=__version__,
        description="Private, traceable personal AI OS backend.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AtlasError, atlas_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    @app.on_event("startup")
    def initialize_local_store() -> None:
        store.initialize()

    @app.get("/healthz", tags=["health"])
    def healthz() -> dict[str, str]:
        return {
            "status": "ok",
            "service": settings.app_name,
            "environment": settings.environment,
            "version": __version__,
        }

    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
