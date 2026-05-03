from pydantic import BaseModel
from typing import List, Dict

class QuestionRequest(BaseModel):
    user_id: str
    topic: str
    difficulty: str


class AnswerRequest(BaseModel):
    user_id: str
    question_id: str
    selected_answer: str

class DifficultyMix(BaseModel):
    easy: float = 0.3
    medium: float = 0.5
    hard: float = 0.2


class TestStartRequest(BaseModel):
    user_id: str
    subjects: List[str]
    total_questions: int = 20
    difficulty_mix: DifficultyMix

class AnswerItem(BaseModel):
    question_id: str
    selected_answer: str


class SubmitRequest(BaseModel):
    session_id: str
    answers: List[AnswerItem]
    
