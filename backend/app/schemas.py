from pydantic import BaseModel, Field
from typing import Any, Literal

class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    source_type: str | None = None
    response_language: Literal["en", "ja"] = "en"

class ProcedureStep(BaseModel):
    instruction: str
    timestamp: str | None = None
    source_ref: str | None = None

class ProcedureUpdate(BaseModel):
    title: str
    description: str = ""
    tools: list[str] = []
    warnings: list[str] = []
    steps: list[ProcedureStep] = []

class ReviewRequest(BaseModel):
    action: str
    note: str = ""

class ProgressRequest(BaseModel):
    procedure_id: int
    trainee_name: str = "Demo Trainee"
    completed_steps: int = 0
    total_steps: int = 0
    quiz_score: int = 0
    completed: bool = False
