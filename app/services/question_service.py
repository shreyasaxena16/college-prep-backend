from app.services.supabase_service import  fetch_questions, save_questions
from app.services.gemini_service import generate_questions


def get_questions(topic: str,subtopic: str = None, difficulty: str= None, limit: int = 5):

    print("topic input:", topic)
    print("subtopic input:", subtopic)
    print("difficulty input:", difficulty)
    existing = fetch_questions(topic,subtopic,difficulty)
    existing_count=len(existing)
    # STEP 1: If enough questions → return DB
    if existing_count >= limit:
        return existing[:limit]
    else:
        return existing[:existing_count]
    




