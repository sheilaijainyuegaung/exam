from app.db.database import SessionLocal, create_db_and_tables
from app.services.rule_profile_service import ensure_default_rule_profile


def init() -> None:
    create_db_and_tables()
    db = SessionLocal()
    try:
        ensure_default_rule_profile(db)
    finally:
        db.close()


if __name__ == "__main__":
    init()

