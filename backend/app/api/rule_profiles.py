from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.enums import RuleSecondLevelMode
from app.models.rule_profile import RuleProfile
from app.schemas.rule_profile import RuleProfileCreate, RuleProfileResponse, RuleProfileUpdate


router = APIRouter()


def _to_response(profile: RuleProfile) -> RuleProfileResponse:
    return RuleProfileResponse(
        id=int(profile.id),
        name=profile.name,
        isActive=bool(profile.is_active),
        maxLevel=int(profile.max_level),
        secondLevelMode=profile.second_level_mode.value
        if hasattr(profile.second_level_mode, "value")
        else str(profile.second_level_mode),
        answerSectionPatterns=profile.answer_section_patterns or [],
        scorePatterns=profile.score_patterns or [],
    )


@router.post("", response_model=RuleProfileResponse)
def create_rule_profile(payload: RuleProfileCreate, db: Session = Depends(get_db)):
    exists = db.query(RuleProfile).filter(RuleProfile.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rule profile name already exists")

    profile = RuleProfile(
        name=payload.name,
        is_active=payload.isActive,
        max_level=payload.maxLevel,
        second_level_mode=RuleSecondLevelMode(payload.secondLevelMode),
        answer_section_patterns=payload.answerSectionPatterns,
        score_patterns=payload.scorePatterns,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _to_response(profile)


@router.get("", response_model=List[RuleProfileResponse])
def list_rule_profiles(db: Session = Depends(get_db)):
    items = db.query(RuleProfile).order_by(RuleProfile.id.desc()).all()
    return [_to_response(item) for item in items]


@router.put("/{rule_profile_id}", response_model=RuleProfileResponse)
def update_rule_profile(rule_profile_id: int, payload: RuleProfileUpdate, db: Session = Depends(get_db)):
    profile = db.query(RuleProfile).filter(RuleProfile.id == rule_profile_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule profile not found")

    if payload.name is not None:
        profile.name = payload.name
    if payload.isActive is not None:
        profile.is_active = payload.isActive
    if payload.maxLevel is not None:
        profile.max_level = payload.maxLevel
    if payload.secondLevelMode is not None:
        profile.second_level_mode = RuleSecondLevelMode(payload.secondLevelMode)
    if payload.answerSectionPatterns is not None:
        profile.answer_section_patterns = payload.answerSectionPatterns
    if payload.scorePatterns is not None:
        profile.score_patterns = payload.scorePatterns

    db.commit()
    db.refresh(profile)
    return _to_response(profile)

