from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.recognitions import router as recognition_router
from app.api.rule_profiles import router as rule_profile_router
from app.core.config import settings
from app.db.database import SessionLocal, create_db_and_tables
from app.services.rule_profile_service import ensure_default_rule_profile


def create_application() -> FastAPI:
    app = FastAPI(title=settings.project_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    settings.resolved_storage_dir.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.pages_dir.mkdir(parents=True, exist_ok=True)
    app.mount(settings.static_url_prefix, StaticFiles(directory=str(settings.resolved_storage_dir)), name="storage")

    app.include_router(recognition_router, prefix=f"{settings.api_v1_prefix}/recognitions", tags=["recognitions"])
    app.include_router(rule_profile_router, prefix=f"{settings.api_v1_prefix}/rule-profiles", tags=["rule-profiles"])

    @app.on_event("startup")
    def _on_startup():
        if settings.auto_create_tables:
            create_db_and_tables()
            db = SessionLocal()
            try:
                ensure_default_rule_profile(db)
            finally:
                db.close()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_application()

