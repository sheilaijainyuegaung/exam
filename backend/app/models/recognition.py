from sqlalchemy import JSON, BigInteger, Column, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.models.enums import DetectedSecondLevelMode, TaskStatus


class RecognitionTask(Base):
    __tablename__ = "recognition_task"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    batch_id = Column(String(64), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_ext = Column(String(16), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_path = Column(String(512), nullable=False)
    status = Column(Enum(TaskStatus, native_enum=False), nullable=False, default=TaskStatus.pending)
    progress = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    rule_profile_id = Column(Integer, ForeignKey("rule_profile.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    finished_at = Column(DateTime, nullable=True)

    rule_profile = relationship("RuleProfile", back_populates="tasks")
    result = relationship("RecognitionResult", back_populates="task", uselist=False, cascade="all,delete-orphan")
    detail = relationship("RecognitionDetail", back_populates="task", uselist=False, cascade="all,delete-orphan")
    hit_logs = relationship("RuleHitLog", back_populates="task", cascade="all,delete-orphan")


class RecognitionResult(Base):
    __tablename__ = "recognition_result"

    task_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("recognition_task.id"), primary_key=True)
    answerPages = Column("answerPages", JSON, nullable=False, default=list)
    mainPages = Column("mainPages", JSON, nullable=False, default=list)
    questionType = Column("questionType", Integer, nullable=False, default=1)
    scores = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    task = relationship("RecognitionTask", back_populates="result")


class RecognitionDetail(Base):
    __tablename__ = "recognition_detail"

    task_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("recognition_task.id"), primary_key=True)
    outline_items = Column(JSON, nullable=False, default=list)
    header_footer_items = Column(JSON, nullable=False, default=list)
    symbol_texts = Column(JSON, nullable=False, default=list)
    detected_max_level = Column(Integer, nullable=False, default=0)
    second_level_mode_detected = Column(
        Enum(DetectedSecondLevelMode, native_enum=False),
        nullable=False,
        default=DetectedSecondLevelMode.unknown,
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    task = relationship("RecognitionTask", back_populates="detail")


class RuleHitLog(Base):
    __tablename__ = "rule_hit_log"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    task_id = Column(BigInteger().with_variant(Integer, "sqlite"), ForeignKey("recognition_task.id"), nullable=False, index=True)
    rule_profile_id = Column(Integer, ForeignKey("rule_profile.id"), nullable=True)
    rule_key = Column(String(128), nullable=False)
    hit_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    task = relationship("RecognitionTask", back_populates="hit_logs")
    rule_profile = relationship("RuleProfile", back_populates="hit_logs")
