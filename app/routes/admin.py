from fastapi import APIRouter,HTTPException
from app.services.gemini_service import generate_questions
from app.services.supabase_service import save_questions
from pydantic import BaseModel
from typing import Dict

router = APIRouter()

class GenerateRequest(BaseModel):
    subject: str
    topic: str
    count: int
    sat_distribution: Dict[str, int]
    difficulty: str

@router.post("/generate")
def admin_generate(req: GenerateRequest):

    # ✅ Validate distribution
    total = sum(req.sat_distribution.values())
    if total != req.count:
        raise HTTPException(
            status_code=400,
            detail="Distribution must sum to total count"
        )

    all_questions = []

    # ✅ Generate per SAT band
    questions = generate_questions(
            subject=req.subject,
            topic=req.topic,
            count=req.count,
            sat_distribution=req.sat_distribution,
            difficulty=req.difficulty
        )

    all_questions.extend(questions)

    # ✅ Save (unchanged structure)
    
    save_questions(
        subject=req.subject,
        topic=req.topic,
        difficulty=req.difficulty,
        questions=all_questions
    )

    return {
        "status": "success",
        "generated": len(all_questions)
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