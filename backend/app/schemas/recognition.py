from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    batchId: str
    taskIds: List[int]
    acceptedCount: int


class TaskStatusResponse(BaseModel):
    taskId: int
    status: str
    progress: int
    errorMessage: Optional[str] = None
    fileName: str


class TaskListItemResponse(BaseModel):
    taskId: int
    batchId: str
    fileName: str
    fileExt: str
    fileSize: int
    status: str
    progress: int
    errorMessage: Optional[str] = None
    createdAt: datetime
    updatedAt: Optional[datetime] = None
    finishedAt: Optional[datetime] = None


class TaskListResponse(BaseModel):
    items: List[TaskListItemResponse]
    total: int
    limit: int
    offset: int


class ClearTasksResponse(BaseModel):
    deletedTaskCount: int


class ScoresNode(BaseModel):
    numbering: str = ""
    rawText: str = ""
    blankText: str = ""
    type: int = 1
    score: float
    childScores: List["ScoresNode"] = Field(default_factory=list)


class RecognitionResultResponse(BaseModel):
    answerPages: List[str]
    mainPages: List[str]
    questionType: int
    scores: ScoresNode


class RecognitionDetailsResponse(BaseModel):
    outlineItems: List[Dict[str, Any]]
    headerFooterItems: List[Dict[str, Any]]
    symbolTexts: List[str]
    detectedMaxLevel: int
    secondLevelModeDetected: str


ScoresNode.model_rebuild()
