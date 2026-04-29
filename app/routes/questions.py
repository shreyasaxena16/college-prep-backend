from fastapi import APIRouter, Query
from services.supabase_service import fetch_questions


import random

router = APIRouter()

@router.get("/questions")
def get_questions(
    topic: str,
    difficulty: str = None,
    limit: int = 5
):
    questions = fetch_questions(topic, difficulty)

    if not questions:
        return {
            "message": "No questions found",
            "data": []
        }

    # 🔀 RANDOMIZE
    random.shuffle(questions)

    # ✂️ LIMIT RESULTS
    selected = questions[:limit]

    return {
        "topic": topic,
        "count": len(selected),
        "questions": selected
    }