from app.config import get_supabase

supabase = get_supabase()

def fetch_questions(category: str, subcategory: str = None, difficulty: str = None):

    query = supabase.table("questions").select("*").eq("category", category)

    if subcategory:
        query = query.eq("subcategory", subcategory)

    if difficulty:
        query = query.eq("difficulty", difficulty)

    response = query.execute()

    return response.data


def save_questions(topic: str, questions: list):

    for q in questions:
        supabase.table("questions").insert({
            "topic": topic,
            "question": q["question"],
            "options": q["options"],
            "correct_answer": q["correct_answer"],
            "used_count": 0
        }).execute()