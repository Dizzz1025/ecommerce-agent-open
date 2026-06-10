from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import health
from app.api.router import api_router
from app.core.config import settings
from app.core.dependencies import get_local_model_manager
from app.core.logging import get_logger


logger = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Minimum end-to-end backend for the ecommerce shopping guide agent.",
    )
    if settings.product_dataset_dir and settings.product_dataset_dir.exists():
        app.mount(
            "/static/dataset",
            StaticFiles(directory=str(settings.product_dataset_dir)),
            name="dataset-static",
        )
    settings.tts_output_dir.mkdir(parents=True, exist_ok=True)
    app.mount(
        "/static/tts",
        StaticFiles(directory=str(settings.tts_output_dir)),
        name="tts-static",
    )
    app.include_router(health.router, tags=["health"])
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.on_event("startup")
    async def log_local_model_diagnostics() -> None:
        manager = get_local_model_manager()
        status = manager.diagnostics()
        logger.info(
            "Local model diagnostics: backend_dir=%s models_dir=%s bge=%s text2vec=%s reranker=%s",
            status.get("backend_dir"),
            status.get("models_dir"),
            _safe_model_status(status.get("bge_embedding", {})),
            _safe_model_status(status.get("text2vec", {})),
            _safe_model_status(status.get("bge_reranker", {})),
        )

    return app


def _safe_model_status(status: dict) -> dict:
    return {
        "resolved_path": status.get("resolved_path") or status.get("path"),
        "path_exists": status.get("path_exists"),
        "loaded": status.get("loaded"),
        "load_error": status.get("load_error"),
    }


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
