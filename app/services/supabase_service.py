from app.config import get_supabase

supabase = get_supabase()

def fetch_questions(subject: str, topic: str = None, difficulty: str = None):

    query = supabase.table("questions").select("*").eq("subject", subject)

    if topic:
        query = query.eq("topic", topic)

    if difficulty:
        query = query.ilike("difficulty", difficulty)

    print("difficulty input:", difficulty)
    print("difficulty repr:", repr(difficulty))
    response = query.execute()
    print("RAW DATA:", response.data)
    return response.data

def save_questions(subject,topic, difficulty, questions):
    for q in questions:
        supabase.table("questions").insert({
            "subject": subject,
            "topic": topic,
            "difficulty": difficulty,
            "sat_band": q.get("sat_band") ,
            "question": q["question"],
            "options": q["options"],
            "correct_answer": q["correct_answer"],
            "explanation": q["explanation"]
        }).execute()



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


#Are the below required?

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
    
def get_student(user_id: str):
    return supabase.table("students") \
        .select("*") \
        .eq("profile_id", user_id) \
        .execute()


def get_profile(user_id: str):
    return supabase.table("profiles") \
        .select("*") \
        .eq("id", user_id) \
        .single() \
        .execute()

   
