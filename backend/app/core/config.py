from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "Exam Recognition Service"
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(default="mysql+pymysql://root:root@127.0.0.1:3306/exam_recognition?charset=utf8mb4")
    storage_dir: str = Field(default="")
    static_url_prefix: str = Field(default="/storage")
    auto_create_tables: bool = Field(default=True)
    libreoffice_cmd: str = Field(default="soffice")
    allowed_origins: str = Field(default="*")
    default_max_level: int = Field(default=8)

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def backend_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def resolved_storage_dir(self) -> Path:
        if self.storage_dir:
            return Path(self.storage_dir).resolve()
        return self.backend_root / "storage"

    @property
    def uploads_dir(self) -> Path:
        return self.resolved_storage_dir / "uploads"

    @property
    def pages_dir(self) -> Path:
        return self.resolved_storage_dir / "pages"

    @property
    def allowed_origins_list(self):
        if self.allowed_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
