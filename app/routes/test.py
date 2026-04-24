from fastapi import APIRouter
from app.models.test_schemas import QuestionRequest, AnswerRequest
from app.services.question_service import get_question
from app.services.attempt_service import submit_answer

router = APIRouter(prefix="/test", tags=["Test"])


@router.post("/question")
def fetch_question(req: QuestionRequest):
    return get_question(req.user_id, req.topic, req.difficulty)


@router.post("/submit")
def submit(req: AnswerRequest):
    return submit_answer(
        req.user_id,
        req.question_id,
        req.selected_answer
    )