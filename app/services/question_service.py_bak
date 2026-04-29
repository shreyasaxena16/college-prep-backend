from app.services.supabase_client import supabase
from app.services.gemini_service import generate_questions


def get_retry_question(user_id):
    res = supabase.table("attempts") \
        .select("question_id") \
        .eq("user_id", user_id) \
        .eq("is_correct", False) \
        .limit(1) \
        .execute()

    if res.data:
        qid = res.data[0]["question_id"]

        q = supabase.table("questions") \
            .select("*") \
            .eq("id", qid) \
            .execute()

        return q.data[0]

    return None


def get_question_from_db(topic, difficulty):
    res = supabase.table("questions") \
        .select("*") \
        .eq("topic", topic) \
        .eq("difficulty", difficulty) \
        .order("used_count", desc=False) \
        .limit(1) \
        .execute()

    return res.data[0] if res.data else None


def save_questions(topic, difficulty, questions):
    for q in questions:
        supabase.table("questions").insert({
            "topic": topic,
            "difficulty": difficulty,
            "question": q["question"],
            "options": q["options"],
            "correct_answer": q["answer"],
            "explanation": q["explanation"]
        }).execute()


def get_question(user_id, topic, difficulty):

    # 1. Retry incorrect
    retry = get_retry_question(user_id)
    if retry:
        return retry

    # 2. Fetch from DB
    db_q = get_question_from_db(topic, difficulty)
    if db_q:
        supabase.table("questions").update({
            "used_count": db_q["used_count"] + 1
        }).eq("id", db_q["id"]).execute()

        return db_q

    # 3. Generate new
    batch = generate_questions(topic, difficulty)
    save_questions(topic, difficulty, batch)

    return batch[0]