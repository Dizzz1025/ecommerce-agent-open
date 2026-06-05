from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import health
from app.api.router import api_router
from app.core.config import settings


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
    app.include_router(health.router, tags=["health"])
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
