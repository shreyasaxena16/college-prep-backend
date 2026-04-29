from fastapi import APIRouter
from services.gemini_service import generate_questions
from services.supabase_service import save_questions

router = APIRouter()

@router.post("/admin/generate")
def admin_generate(topic: str, count: int = 50):

    questions = generate_questions(topic, count)
    save_questions(topic, questions)

    return {
        "status": "success",
        "topic": topic,
        "generated": count
    }