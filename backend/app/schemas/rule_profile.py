from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RuleProfileBase(BaseModel):
    name: str = Field(..., max_length=128)
    isActive: bool = True
    maxLevel: int = Field(default=8, ge=1, le=8)
    secondLevelMode: str = Field(default="auto", pattern="^(auto|restart|continuous)$")
    answerSectionPatterns: List[str] = Field(default_factory=list)
    scorePatterns: List[str] = Field(default_factory=list)


class RuleProfileCreate(RuleProfileBase):
    pass


class RuleProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)
    isActive: Optional[bool] = None
    maxLevel: Optional[int] = Field(default=None, ge=1, le=8)
    secondLevelMode: Optional[str] = Field(default=None, pattern="^(auto|restart|continuous)$")
    answerSectionPatterns: Optional[List[str]] = None
    scorePatterns: Optional[List[str]] = None


class RuleProfileResponse(RuleProfileBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
