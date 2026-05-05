from fastapi import APIRouter
from app.services.gemini_service import generate_questions
from app.services.supabase_service import save_questions
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class GenerateRequest(BaseModel):
    subject: str
    difficulty: str = "medium"
    count: int = 10
    topic: Optional[str] = None

@router.post("/generate")
# def admin_generate(subject: str, topic:str=None, count: int = 50,difficulty: str='medium'):
#     subject = subject.capitalize()
#     difficulty = difficulty.lower()
#     if subject not in ["Math", "English"]:
#         return {"error": "Invalid subject"}

#     if difficulty not in ["easy", "medium", "hard"]:
#         return {"error": "Invalid difficulty"}
    
#     questions = generate_questions(subject, topic, count,difficulty)
#     save_questions(subject, topic, difficulty, questions)

#     return {
#         "status": "success",
#         "Subject": subject,
#         "generated": count
#     }

@router.post("/generate")
def admin_generate(req: GenerateRequest):

    questions = generate_questions(
        req.topic or req.subject,
        req.count,
        req.difficulty
    )

    save_questions(req.subject, req.topic, req.difficulty, questions)

    return {
        "status": "success",
        "generated": len(questions)
    }

@router.get("/stats")
def get_stats():
    from app.services.supabase_service import get_supabase

    supabase = get_supabase()

    res = supabase.table("questions").select("subject,difficulty").execute()

    data = res.data

    stats = {}

    for q in data:
        subject = (q.get("subject") or "unknown").title()
        difficulty = (q.get("difficulty") or "unknown").lower()

        stats.setdefault(subject, {})
        stats[subject].setdefault(difficulty, 0)

        stats[subject][difficulty] += 1

    return stats