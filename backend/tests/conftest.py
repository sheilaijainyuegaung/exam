import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


BASE_DIR = Path(__file__).resolve().parents[1]
TEST_DB = BASE_DIR / "test_api.db"
TEST_STORAGE = BASE_DIR / "test_storage"

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["AUTO_CREATE_TABLES"] = "true"
os.environ["STORAGE_DIR"] = str(TEST_STORAGE)
os.environ["STATIC_URL_PREFIX"] = "/storage"

from app.main import create_application  # noqa: E402
from app.db.database import SessionLocal, create_db_and_tables, engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def setup_env():
    if TEST_DB.exists():
        TEST_DB.unlink()
    if TEST_STORAGE.exists():
        shutil.rmtree(TEST_STORAGE, ignore_errors=True)
    TEST_STORAGE.mkdir(parents=True, exist_ok=True)
    create_db_and_tables()
    yield
    engine.dispose()
    if TEST_DB.exists():
        TEST_DB.unlink()
    if TEST_STORAGE.exists():
        shutil.rmtree(TEST_STORAGE, ignore_errors=True)


@pytest.fixture()
def app():
    return create_application()


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
