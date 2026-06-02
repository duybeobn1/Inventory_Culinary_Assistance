from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StepExtractRequest(BaseModel):
    recipe_id: str
    markdown: str


class RecipeStepOut(BaseModel):
    step_number: int
    instruction: str
    duration_seconds: int
    ingredients_used: list[str]
    tools_needed: list[str]


class CreateSessionRequest(BaseModel):
    recipe_id: str


class CreateSessionResponse(BaseModel):
    session_id: str
    recipe_name: str
    total_steps: int
    current_step: int
    steps: list[RecipeStepOut]


class SessionState(BaseModel):
    session_id: str
    recipe_name: str
    total_steps: int
    current_step: int
    status: str
    started_at: datetime
    elapsed_seconds: int


class OcrFrameRequest(BaseModel):
    image: str


class OcrFrameResponse(BaseModel):
    detected: str
    suggestion: str
    is_correct: bool
    mode: str


class AdvanceStepResponse(BaseModel):
    current_step: int
    total_steps: int
    instruction: str
    session_complete: bool
