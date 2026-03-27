from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import RuleSecondLevelMode
from app.models.rule_profile import RuleProfile
from app.services.rule_engine import DEFAULT_SCORE_PATTERNS


DEFAULT_ANSWER_SECTION_PATTERNS = [
    "参考答案",
    "答案页",
    "答案",
    "解析部分",
]


def ensure_default_rule_profile(db: Session) -> RuleProfile:
    profile = db.query(RuleProfile).filter(RuleProfile.is_active.is_(True)).first()
    if profile:
        return profile

    profile = RuleProfile(
        name="default-rule-profile",
        is_active=True,
        max_level=settings.default_max_level,
        second_level_mode=RuleSecondLevelMode.auto,
        answer_section_patterns=DEFAULT_ANSWER_SECTION_PATTERNS,
        score_patterns=DEFAULT_SCORE_PATTERNS,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def get_rule_profile_or_default(db: Session, rule_profile_id: Optional[int]) -> RuleProfile:
    if rule_profile_id:
        profile = db.query(RuleProfile).filter(RuleProfile.id == rule_profile_id).first()
        if profile:
            return profile
    return ensure_default_rule_profile(db)

