import random
from services.supabase_service import fetch_questions

def build_test(category: str, subcategory: str = None, difficulty: str = None, limit: int = 10):

    questions = fetch_questions(category, subcategory, difficulty)

    if not questions:
        return []

    random.shuffle(questions)

    return questions[:limit]




