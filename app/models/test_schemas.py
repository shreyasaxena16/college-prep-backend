from pydantic import BaseModel

class QuestionRequest(BaseModel):
    user_id: str
    topic: str
    difficulty: str


class AnswerRequest(BaseModel):
    user_id: str
    question_id: str
    selected_answer: str