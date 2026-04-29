from app.services.gemini_service import generate_questions
from app.services.supabase_service import fetch_questions, save_questions

THRESHOLD = 5


def get_questions(topic: str, limit: int = 5):

    existing = fetch_questions(topic)

    # STEP 1: If enough questions → return DB
    if len(existing) >= limit:
        return existing[:limit]

    # STEP 2: Not enough → generate more
    new_questions = generate_questions(topic, count=20)

    save_questions(topic, new_questions)

    # STEP 3: Return fresh mix
    updated = fetch_questions(topic)
    return updated[:limit]


def refill_if_needed(topic: str):

    existing = fetch_questions(topic)

    if len(existing) < THRESHOLD:
        new_questions = generate_questions(topic, count=50)
        save_questions(topic, new_questions)