from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.models.enums import RuleSecondLevelMode


class RuleProfile(Base):
    __tablename__ = "rule_profile"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, default=True)
    max_level = Column(Integer, nullable=False, default=8)
    second_level_mode = Column(
        Enum(RuleSecondLevelMode, native_enum=False),
        nullable=False,
        default=RuleSecondLevelMode.auto,
    )
    answer_section_patterns = Column(JSON, nullable=False, default=list)
    score_patterns = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    tasks = relationship("RecognitionTask", back_populates="rule_profile")
    hit_logs = relationship("RuleHitLog", back_populates="rule_profile")

