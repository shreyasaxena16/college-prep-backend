from fastapi import APIRouter
from app.services.gemini_service import generate_questions
from app.services.supabase_service import save_questions

router = APIRouter()

@router.post("/admin/generate")
def admin_generate(topic: str, count: int = 50,difficulty: str='medium'):

    questions = generate_questions(topic, count,difficulty)
    save_questions(topic, questions)

    return {
        "status": "success",
        "topic": topic,
        "generated": count
    }